"""Download one MAIN Amazon Reviews 2023 image per selected source item.

The downloader is deliberately conservative: it prefers `large`, then `hi_res`,
then `thumb`; validates the actual image bytes with Pillow; rate-limits requests
per host; retries transient failures; and records one manifest row per item.

Run:
python src/data/Amazon2023/download_amr_images.py \
  --out-dir data/processed/amr-home-v1 --resume-images
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import random
import socket
import ssl
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'negatives'))
from sean_common import read_csv, write_csv

from amr_io import (
    IMAGE_MANIFEST_FIELDS, is_safe_image_url, normalize_url, sha256_file,
    write_checksums, write_json_lf,
)

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is part of the project env
    Image = None


@dataclass
class DownloadSettings:
    variant_order: tuple = ('large', 'hi_res', 'thumb')
    workers: int = 4
    requests_per_second: float = 2.0
    timeout: float = 30.0
    retries: int = 3
    max_bytes: int = 20_000_000
    min_dimension: int = 64
    max_dimension: int = 10000
    max_pixels: int = 60_000_000
    allowed_hosts: tuple = ('m.media-amazon.com',)
    allowed_formats: tuple = ('JPEG',)
    low_resolution_threshold: int = 224
    backoff_base: float = 2.0
    backoff_cap: float = 60.0
    jitter: float = 0.5
    retry_after_cap: float = 120.0
    user_agent: str = 'Mozilla/5.0 (compatible; cse6740-amr/1.0)'


class DownloadError(Exception):
    def __init__(self, kind, message, retry_after=None):
        super().__init__(message)
        self.kind = kind
        self.retry_after = retry_after


class HostRateLimiter:
    """Thread-safe per-host token bucket (spaces requests evenly)."""

    def __init__(self, rate, sleep=time.sleep, clock=time.monotonic):
        self.rate = float(rate)
        self.sleep = sleep
        self.clock = clock
        self.lock = threading.Lock()
        self.next_allowed = {}

    def acquire(self, host):
        if self.rate <= 0:
            return
        with self.lock:
            now = self.clock()
            next_allowed = self.next_allowed.get(host, now)
            wait = max(0.0, next_allowed - now)
            self.next_allowed[host] = max(now, next_allowed) + (1.0 / self.rate)
        if wait > 0:
            self.sleep(wait)


def _parse_retry_after(error):
    headers = getattr(error, 'headers', None)
    if not headers:
        return None
    value = headers.get('Retry-After')
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _read_response(response, max_bytes):
    chunks = []
    total = 0
    while True:
        chunk = response.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise DownloadError('too_large', f'response exceeds {max_bytes} bytes')
        chunks.append(chunk)
    if not chunks:
        raise DownloadError('empty_response', 'empty response body')
    return b''.join(chunks)


def _fetch_once(url, settings, limiter, opener=None):
    if opener is None:
        opener = urlopen
    host = (urlparse(url).hostname or '').casefold()
    limiter.acquire(host)
    request = Request(url, headers={
        'User-Agent': settings.user_agent,
        'Accept': 'image/avif,image/webp,image/jpeg,image/png,*/*',
    })
    try:
        with opener(request, timeout=settings.timeout) as response:
            status = getattr(response, 'status', 200)
            headers = getattr(response, 'headers', None)
            content_type = headers.get('Content-Type', '') if headers is not None else ''
            final_url = response.geturl() if hasattr(response, 'geturl') else url
            if final_url and not is_safe_image_url(final_url, settings.allowed_hosts):
                raise DownloadError('unsafe_redirect', f'redirected to {final_url}')
            if status != 200:
                raise DownloadError(f'http_{status}', f'HTTP {status}')
            lowered = (content_type or '').casefold()
            if lowered.startswith('text/') or lowered.startswith('application/json'):
                raise DownloadError('invalid_content_type', f'content-type {content_type}')
            return _read_response(response, settings.max_bytes), status, content_type
    except HTTPError as exc:
        raise DownloadError(f'http_{exc.code}', f'HTTP {exc.code}', _parse_retry_after(exc))
    except DownloadError:
        raise
    except (URLError, TimeoutError, socket.timeout, ssl.SSLError, OSError) as exc:
        raise DownloadError('network', f'{type(exc).__name__}: {exc}')
    except Exception as exc:
        raise DownloadError('request_error', f'{type(exc).__name__}: {exc}')


def _validate_image(data, settings):
    if Image is None:
        raise DownloadError('missing_pillow', 'Pillow is not installed')
    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format = image.format or ''
            width, height = image.size
            image.verify()
    except Exception as exc:
        raise DownloadError('invalid_image', f'{type(exc).__name__}: {exc}')
    if image_format not in settings.allowed_formats:
        raise DownloadError('unsupported_format', f'format {image_format or "unknown"}')
    if width < settings.min_dimension or height < settings.min_dimension:
        raise DownloadError('too_small', f'{width}x{height} below minimum')
    if width > settings.max_dimension or height > settings.max_dimension:
        raise DownloadError('too_big', f'{width}x{height} above maximum dimension')
    if width * height > settings.max_pixels:
        raise DownloadError('too_many_pixels', f'{width}x{height} above pixel cap')
    low_resolution = int(min(width, height) < settings.low_resolution_threshold)
    return image_format, width, height, low_resolution


def _safe_target(image_root, relative):
    relative = PurePosixPath(relative)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise DownloadError('unsafe_path', f'unsafe image_path {relative}')
    root = Path(image_root).resolve()
    target = root.joinpath(*relative.parts).resolve()
    if not target.is_relative_to(root):
        raise DownloadError('unsafe_path', f'image_path escapes image root {relative}')
    return target


def _write_atomic(target, data):
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + '.part')
    try:
        with open(temp, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temp.replace(target)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass


def _success_row(row, variant, url, status, content_type, attempts, data, info):
    image_format, width, height, low_resolution = info
    return {
        'item_id': row['item_id'],
        'image_path': row['image_path'],
        'source_variant': variant,
        'source_url': url,
        'http_status': str(status),
        'content_type': content_type or '',
        'attempts': str(attempts),
        'sha256': hashlib.sha256(data).hexdigest(),
        'bytes': str(len(data)),
        'format': image_format,
        'width': str(width),
        'height': str(height),
        'low_resolution': str(low_resolution),
        'error_class': '',
        'error': '',
    }


def _error_row(row, attempts, variant, url, status, content_type, error_class, error):
    return {
        'item_id': row['item_id'],
        'image_path': row['image_path'],
        'source_variant': variant,
        'source_url': url,
        'http_status': str(status or ''),
        'content_type': content_type or '',
        'attempts': str(attempts),
        'sha256': '',
        'bytes': '0',
        'format': '',
        'width': '',
        'height': '',
        'low_resolution': '0',
        'error_class': error_class or 'all_variants_failed',
        'error': (error or 'all variants failed')[:300],
    }


def _resume_row(row, target, settings):
    if not target.is_file():
        return None
    try:
        data = target.read_bytes()
        info = _validate_image(data, settings)
    except Exception:
        try:
            target.unlink()
        except OSError:
            pass
        return None
    digest = hashlib.sha256(data).hexdigest()
    image_format, width, height, low_resolution = info
    return {
        'item_id': row['item_id'],
        'image_path': row['image_path'],
        'source_variant': 'resumed',
        'source_url': '',
        'http_status': '',
        'content_type': '',
        'attempts': '0',
        'sha256': digest,
        'bytes': str(len(data)),
        'format': image_format,
        'width': str(width),
        'height': str(height),
        'low_resolution': str(low_resolution),
        'error_class': '',
        'error': '',
    }


def download_one(row, image_root, settings, limiter, opener=None):
    if opener is None:
        opener = urlopen
    target = _safe_target(image_root, row['image_path'])
    attempts = 0
    last_variant = ''
    last_url = ''
    last_status = ''
    last_content_type = ''
    last_class = ''
    last_error = ''
    for variant in settings.variant_order:
        url = normalize_url(row.get(f'image_url_{variant}', ''))
        if not url:
            continue
        last_variant, last_url = variant, url
        if not is_safe_image_url(url, settings.allowed_hosts):
            last_class, last_error = 'unsafe_url', f'unsafe image URL: {url}'
            continue
        for attempt in range(1, max(1, settings.retries) + 1):
            attempts += 1
            try:
                data, status, content_type = _fetch_once(url, settings, limiter, opener)
                info = _validate_image(data, settings)
                _write_atomic(target, data)
                return _success_row(row, variant, url, status, content_type, attempts, data, info)
            except DownloadError as exc:
                last_class = exc.kind
                last_error = str(exc)
                if exc.kind.startswith('http_'):
                    last_status = exc.kind.split('_', 1)[1]
                if exc.kind in {
                    'unsafe_url', 'invalid_content_type', 'invalid_image',
                    'unsupported_format', 'too_large', 'too_small', 'too_big',
                    'too_many_pixels', 'empty_response', 'missing_pillow',
                }:
                    break
                if exc.kind.startswith('http_'):
                    code = last_status
                    if code.isdigit():
                        code_number = int(code)
                        if 400 <= code_number < 500 and code_number not in (408, 409, 425, 429):
                            break
                if attempt >= settings.retries:
                    break
                wait = min(settings.backoff_cap, settings.backoff_base * (2 ** (attempt - 1)))
                wait += random.uniform(0.0, settings.jitter)
                if exc.retry_after is not None:
                    wait = min(settings.retry_after_cap, exc.retry_after)
                time.sleep(max(0.0, wait))
            except Exception as exc:
                last_class, last_error = 'request_error', f'{type(exc).__name__}: {exc}'
                if attempt >= settings.retries:
                    break
                wait = min(settings.backoff_cap, settings.backoff_base * (2 ** (attempt - 1)))
                time.sleep(max(0.0, wait + random.uniform(0.0, settings.jitter)))
    return _error_row(
        row, attempts, last_variant, last_url, last_status, last_content_type,
        last_class, last_error,
    )


def run_download(items, image_root, settings, existing_rows=None, force=False, limit=None, progress_every=100):
    existing = {row['item_id']: row for row in (existing_rows or [])}
    if limit is not None and limit >= 0:
        items = items[:limit]
    limiter = HostRateLimiter(settings.requests_per_second)
    rows = []
    stats = {
        'requested': len(items), 'ok': 0, 'resumed_valid': 0, 'failed': 0,
        'low_resolution': 0, 'variants_used': {}, 'failure_reasons': {},
    }

    def process(row):
        if not force:
            target = _safe_target(image_root, row['image_path'])
            resumed = _resume_row(row, target, settings)
            if resumed is not None:
                previous = existing.get(row['item_id'])
                if previous and previous.get('sha256') == resumed['sha256'] and not previous.get('error'):
                    resumed['source_variant'] = previous.get('source_variant', 'resumed')
                    resumed['source_url'] = previous.get('source_url', '')
                    resumed['http_status'] = previous.get('http_status', '')
                    resumed['content_type'] = previous.get('content_type', '')
                return resumed, True
        return download_one(row, image_root, settings, limiter), False

    with ThreadPoolExecutor(max_workers=max(1, settings.workers)) as pool:
        futures = [pool.submit(process, row) for row in items]
        for index, future in enumerate(as_completed(futures), 1):
            row, resumed = future.result()
            rows.append(row)
            if row['error']:
                stats['failed'] += 1
                stats['failure_reasons'][row['error_class']] = stats['failure_reasons'].get(row['error_class'], 0) + 1
            elif resumed:
                stats['resumed_valid'] += 1
            else:
                stats['ok'] += 1
                stats['variants_used'][row['source_variant']] = stats['variants_used'].get(row['source_variant'], 0) + 1
            if not row['error'] and row.get('low_resolution') == '1':
                stats['low_resolution'] += 1
            if progress_every and index % progress_every == 0:
                print(f'images processed {index}/{len(items)}; failed={stats["failed"]}', flush=True)
    rows.sort(key=lambda row: row['item_id'])
    stats['complete'] = stats['failed'] == 0
    return rows, stats


def read_image_manifest(path):
    path = Path(path)
    if not path.is_file():
        return []
    return read_csv(path)


def write_download_results(out_dir, rows, stats, items_sha256, config_version=''):
    out_dir = Path(out_dir)
    write_csv(out_dir / 'image_manifest.csv', rows, IMAGE_MANIFEST_FIELDS)
    manifest_path = out_dir / 'manifest.json'
    manifest = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.setdefault('images', {})
    manifest['images'].update({
        'requested': stats['requested'],
        'ok': stats['ok'],
        'resumed_valid': stats['resumed_valid'],
        'failed': stats['failed'],
        'low_resolution': stats.get('low_resolution', 0),
        'complete': stats['complete'],
        'variants_used': stats['variants_used'],
        'failure_reasons': stats['failure_reasons'],
        'items_sha256': items_sha256,
    })
    if config_version:
        manifest['version'] = manifest.get('version', config_version)
    write_json_lf(manifest_path, manifest)
    write_checksums(out_dir, [
        'items.csv', 'filter_summary.csv', 'sampling_summary.csv', 'dfa_summary.csv',
        'second_level_counts.csv', 'exclusion_summary.csv', 'no_main_images.csv',
        'config.json', 'validation.json', 'manifest.json', 'image_manifest.csv',
    ])
    return manifest


def settings_from_config(config, args):
    images = config['images']
    return DownloadSettings(
        variant_order=tuple(images.get('variant_order', ['large', 'hi_res', 'thumb'])),
        workers=args.workers if args.workers is not None else images.get('workers', 4),
        requests_per_second=(
            args.requests_per_second if args.requests_per_second is not None
            else images.get('requests_per_second', 2.0)
        ),
        timeout=args.timeout if args.timeout is not None else images.get('timeout_seconds', 30),
        retries=args.retries if args.retries is not None else images.get('retries', 3),
        max_bytes=args.max_bytes if args.max_bytes is not None else images.get('max_bytes', 20_000_000),
        min_dimension=args.min_dimension if args.min_dimension is not None else images.get('min_dimension', 64),
        max_dimension=images.get('max_dimension', 10000),
        max_pixels=args.max_pixels if args.max_pixels is not None else images.get('max_pixels', 60_000_000),
        allowed_hosts=tuple(images.get('allowed_hosts', ['m.media-amazon.com'])),
        allowed_formats=tuple(images.get('allowed_formats', ['JPEG'])),
        low_resolution_threshold=images.get('low_resolution_threshold', 224),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/amr_home_v1.json')
    parser.add_argument('--out-dir', default='data/processed/amr-home-v1')
    parser.add_argument('--items-csv', default=None)
    parser.add_argument('--image-root', default=None)
    parser.add_argument('--workers', type=int, default=None)
    parser.add_argument('--requests-per-second', type=float, default=None)
    parser.add_argument('--timeout', type=float, default=None)
    parser.add_argument('--retries', type=int, default=None)
    parser.add_argument('--max-bytes', type=int, default=None)
    parser.add_argument('--min-dimension', type=int, default=None)
    parser.add_argument('--max-pixels', type=int, default=None)
    parser.add_argument('--resume-images', action='store_true')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    out_dir = Path(args.out_dir)
    items_csv = Path(args.items_csv) if args.items_csv else out_dir / 'items.csv'
    image_root = Path(args.image_root) if args.image_root else out_dir / 'images'
    if not items_csv.is_file():
        raise SystemExit(f'items.csv not found: {items_csv}')
    items = read_csv(items_csv)
    if args.limit is not None:
        items = items[:args.limit]
    items_sha256 = sha256_file(items_csv)
    manifest_path = out_dir / 'manifest.json'
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text(encoding='utf-8'))
        expected = previous.get('images', {}).get('items_sha256', '')
        if expected and expected != items_sha256 and not args.force:
            raise SystemExit('items.csv changed since the previous run; use --force or a new out-dir.')
    if args.dry_run:
        print(json.dumps({
            'items': len(items), 'items_sha256': items_sha256,
            'settings': {
                'variant_order': list(settings_from_config(config, args).variant_order),
                'workers': settings_from_config(config, args).workers,
                'requests_per_second': settings_from_config(config, args).requests_per_second,
            },
        }, ensure_ascii=False, indent=2))
        return 0

    settings = settings_from_config(config, args)
    existing = read_image_manifest(out_dir / 'image_manifest.csv')
    rows, stats = run_download(
        items, image_root, settings, existing_rows=existing,
        force=args.force, limit=None,
    )
    write_download_results(out_dir, rows, stats, items_sha256, config_version=config['version'])
    print(json.dumps(stats, ensure_ascii=False, indent=2), flush=True)
    return 0 if stats['failed'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
