"""Safeguards for the Amazon Reviews 2023 image downloader."""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'data' / 'Amazon2023'))
sys.path.insert(0, str(ROOT / 'src' / 'negatives'))

from PIL import Image

import download_amr_images as downloader
from sean_common import write_csv


def jpeg_bytes(size=(80, 80), color=(20, 120, 200)):
    buffer = io.BytesIO()
    Image.new('RGB', size, color).save(buffer, 'JPEG')
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, data, status=200, content_type='image/jpeg', url=''):
        self.data = data
        self.status = status
        self.headers = {'Content-Type': content_type}
        self.url = url
        self.position = 0

    def read(self, size=-1):
        if size is None or size < 0:
            chunk = self.data[self.position:]
            self.position = len(self.data)
            return chunk
        chunk = self.data[self.position:self.position + size]
        self.position += len(chunk)
        return chunk

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def settings(**overrides):
    values = dict(
        workers=1, requests_per_second=1000.0, timeout=5, retries=2,
        max_bytes=20_000_000, min_dimension=64, max_dimension=10000,
        max_pixels=60_000_000, allowed_formats=('JPEG',),
        low_resolution_threshold=224,
    )
    values.update(overrides)
    return downloader.DownloadSettings(**values)


def row(item_id='B000000001', image_path='chair/ab/B000000001.jpg'):
    base = 'https://m.media-amazon.com/images/I/B000000001'
    return {
        'item_id': item_id,
        'image_path': image_path,
        'image_url_large': base + '._AC_.jpg',
        'image_url_hi_res': base + '._AC_SL1500_.jpg',
        'image_url_thumb': base + '._AC_US75_.jpg',
        'product_type': 'CHAIR',
    }


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image_root = self.root / 'images'

    def tearDown(self):
        self.temp.cleanup()

    def test_successful_large_download(self):
        data = jpeg_bytes()
        def fake_opener(request, timeout):
            return FakeResponse(data, url=request.full_url)
        result = downloader.download_one(row(), self.image_root, settings(), downloader.HostRateLimiter(1000), opener=fake_opener)
        self.assertEqual(result['error'], '')
        self.assertEqual(result['source_variant'], 'large')
        target = self.image_root / 'chair' / 'ab' / 'B000000001.jpg'
        self.assertEqual(target.read_bytes(), data)
        self.assertEqual(result['sha256'], hashlib.sha256(data).hexdigest())
        self.assertFalse(list(self.image_root.rglob('*.part')))

    def test_large_404_falls_back_to_hi_res(self):
        data = jpeg_bytes()
        calls = []
        def fake_opener(request, timeout):
            calls.append(request.full_url)
            if '._AC_.jpg' in request.full_url and 'SL1500' not in request.full_url:
                raise HTTPError(request.full_url, 404, 'Not Found', {}, None)
            return FakeResponse(data, url=request.full_url)
        result = downloader.download_one(row(), self.image_root, settings(), downloader.HostRateLimiter(1000), opener=fake_opener)
        self.assertEqual(result['error'], '')
        self.assertEqual(result['source_variant'], 'hi_res')
        self.assertEqual(len(calls), 2)

    def test_all_variants_fail(self):
        def fake_opener(request, timeout):
            raise HTTPError(request.full_url, 404, 'Not Found', {}, None)
        result = downloader.download_one(row(), self.image_root, settings(), downloader.HostRateLimiter(1000), opener=fake_opener)
        self.assertNotEqual(result['error'], '')
        self.assertEqual(result['error_class'], 'http_404')
        self.assertFalse((self.image_root / 'chair' / 'ab' / 'B000000001.jpg').exists())
        self.assertFalse(list(self.image_root.rglob('*.part')))

    def test_unsafe_url_never_opens(self):
        unsafe = row()
        unsafe['image_url_large'] = 'https://evil.example/images/I/X._AC_.jpg'
        unsafe['image_url_hi_res'] = ''
        unsafe['image_url_thumb'] = ''
        def fake_opener(request, timeout):
            raise AssertionError('opener should not be called')
        result = downloader.download_one(unsafe, self.image_root, settings(), downloader.HostRateLimiter(1000), opener=fake_opener)
        self.assertEqual(result['error_class'], 'unsafe_url')

    def test_invalid_image_falls_back(self):
        good = jpeg_bytes()
        def fake_opener(request, timeout):
            if '._AC_.jpg' in request.full_url and 'SL1500' not in request.full_url:
                return FakeResponse(b'<html>not an image</html>', content_type='text/html', url=request.full_url)
            return FakeResponse(good, url=request.full_url)
        result = downloader.download_one(row(), self.image_root, settings(), downloader.HostRateLimiter(1000), opener=fake_opener)
        self.assertEqual(result['error'], '')
        self.assertEqual(result['source_variant'], 'hi_res')

    def test_max_bytes(self):
        data = jpeg_bytes()
        def fake_opener(request, timeout):
            return FakeResponse(data, url=request.full_url)
        result = downloader.download_one(
            row(), self.image_root, settings(max_bytes=10, retries=1),
            downloader.HostRateLimiter(1000), opener=fake_opener,
        )
        self.assertEqual(result['error_class'], 'too_large')

    def test_resume_skips_valid_existing_file(self):
        data = jpeg_bytes()
        target = self.image_root / 'chair' / 'ab' / 'B000000001.jpg'
        target.parent.mkdir(parents=True)
        target.write_bytes(data)
        existing = downloader._resume_row(row(), target, settings())
        self.assertIsNotNone(existing)
        self.assertEqual(existing['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(existing['source_variant'], 'resumed')
        with mock.patch('download_amr_images.urlopen', side_effect=AssertionError('should not fetch')):
            rows, stats = downloader.run_download([row()], self.image_root, settings(), existing_rows=[existing])
        self.assertEqual(stats['resumed_valid'], 1)
        self.assertEqual(stats['failed'], 0)
        self.assertEqual(rows[0]['error'], '')

    def test_retry_after_429(self):
        data = jpeg_bytes()
        calls = {'count': 0}
        def fake_opener(request, timeout):
            calls['count'] += 1
            if calls['count'] == 1:
                raise HTTPError(request.full_url, 429, 'Too Many Requests', {'Retry-After': '0'}, None)
            return FakeResponse(data, url=request.full_url)
        with mock.patch('download_amr_images.time.sleep'):
            result = downloader.download_one(
                row(), self.image_root, settings(retries=2),
                downloader.HostRateLimiter(1000), opener=fake_opener,
            )
        self.assertEqual(result['error'], '')
        self.assertEqual(calls['count'], 2)
        self.assertEqual(result['attempts'], '2')

    def test_rate_limiter_spacing(self):
        sleeps = []
        clock = {'value': 0.0}

        def fake_sleep(seconds):
            sleeps.append(seconds)
            clock['value'] += seconds

        limiter = downloader.HostRateLimiter(2.0, sleep=fake_sleep, clock=lambda: clock['value'])
        limiter.acquire('host')
        limiter.acquire('host')
        limiter.acquire('host')
        self.assertEqual(sleeps, [0.5, 0.5])

    def test_resume_items_hash_mismatch(self):
        out = self.root / 'out'
        out.mkdir()
        write_csv(out / 'items.csv', [row()], ['item_id', 'image_path', 'image_url_large', 'image_url_hi_res', 'image_url_thumb', 'product_type'])
        (out / 'manifest.json').write_text(json.dumps({'images': {'items_sha256': 'wrong'}}), encoding='utf-8')
        with mock.patch('download_amr_images.urlopen', side_effect=AssertionError('should not fetch')):
            with self.assertRaises(SystemExit):
                downloader.main(['--config', str(ROOT / 'configs' / 'amr_home_v1.json'), '--out-dir', str(out)])

    def test_dry_run_no_network(self):
        out = self.root / 'out'
        out.mkdir()
        write_csv(out / 'items.csv', [row()], ['item_id', 'image_path', 'image_url_large', 'image_url_hi_res', 'image_url_thumb', 'product_type'])
        with mock.patch('download_amr_images.urlopen', side_effect=AssertionError('should not fetch')):
            self.assertEqual(downloader.main([
                '--config', str(ROOT / 'configs' / 'amr_home_v1.json'),
                '--out-dir', str(out), '--dry-run',
            ]), 0)


if __name__ == '__main__':
    unittest.main()
