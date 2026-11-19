"""Streaming IO and normalization helpers for Amazon Reviews 2023 metadata.

This module contains no filtering policy beyond the configurable category rules
passed in from build_amr_items.py. It is intentionally dependency-free apart
from the Python standard library.
"""
import gzip
import hashlib
import html
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

PRODUCT_TYPES = [
    'CHAIR', 'RUG', 'TABLE', 'WALL_ART', 'SOFA',
    'HOME_FURNITURE_AND_DECOR', 'STOOL_SEATING', 'OTTOMAN', 'PILLOW', 'HOME',
]

ITEM_FIELDS = [
    'item_id', 'title', 'image_path', 'product_type', 'node', 'color',
    'material', 'group_id', 'split', 'main_image_id',
    'image_url_large', 'image_url_hi_res', 'image_url_thumb',
    'year', 'year_source', 'date_first_available', 'rating_number',
    'average_rating', 'price', 'store', 'main_category',
    'category_l2', 'category_leaf', 'classification_rule',
    'source_file', 'source_line',
]

IMAGE_MANIFEST_FIELDS = [
    'item_id', 'image_path', 'source_variant', 'source_url', 'http_status',
    'content_type', 'attempts', 'sha256', 'bytes', 'format', 'width',
    'height', 'low_resolution', 'error_class', 'error',
]

NO_MAIN_FIELDS = ['item_id', 'product_type', 'category_path', 'reason', 'source_line']

DATE_FORMATS = (
    '%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y',
    '%d %B %Y', '%d %b %Y', '%Y-%m-%d', '%Y/%m/%d',
    '%m/%d/%Y', '%m/%d/%y',
)

IMAGE_ID_RE = re.compile(r'[A-Za-z0-9+_-]+')
ASIN_RE = re.compile(r'[A-Za-z0-9]{10}')


def norm(value):
    """Case-fold and collapse whitespace after undoing HTML entities."""
    return re.sub(r'\s+', ' ', html.unescape('' if value is None else str(value)).casefold()).strip()


def clean_text(value):
    """Human-readable cleaned text, preserving case and punctuation."""
    if value is None:
        return ''
    return re.sub(r'\s+', ' ', html.unescape(str(value))).strip()


def tokens(value):
    """Word tokens used for phrase matching. '&' is kept as its own token."""
    return re.findall(r'[\w&]+', norm(value))


def phrase_in(segment_tokens, phrase):
    """True when phrase tokens occur contiguously in segment_tokens."""
    wanted = tokens(phrase)
    if not wanted:
        return False
    size = len(wanted)
    return any(segment_tokens[i:i + size] == wanted for i in range(len(segment_tokens) - size + 1))


def any_phrase_in(segments, phrases):
    return any(phrase_in(segment, phrase) for segment in segments for phrase in phrases)


def detail_string(value):
    """Flatten details.Color / details.Material values into one CSV cell."""
    if value is None:
        return ''
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, (list, tuple, set)):
        return '; '.join(clean_text(item) for item in value if clean_text(item))
    if isinstance(value, dict):
        return '; '.join(f'{clean_text(k)}: {clean_text(v)}' for k, v in value.items() if clean_text(v))
    return clean_text(value)


def safe_item_id(value):
    return bool(ASIN_RE.fullmatch(clean_text(value)))


def normalize_url(value):
    url = clean_text(value)
    if url.startswith('http://'):
        url = 'https://' + url[len('http://'):]
    return url


def image_id_from_url(url):
    try:
        path = urlparse(normalize_url(url)).path
    except Exception:
        return ''
    name = PurePosixPath(path).name
    image_id = name.split('.', 1)[0]
    return image_id if IMAGE_ID_RE.fullmatch(image_id) else ''


def is_safe_image_url(url, allowed_hosts=('m.media-amazon.com',)):
    """Only Amazon media URLs under /images/I/ are accepted."""
    url = normalize_url(url)
    if not url or any(ord(ch) < 32 for ch in url):
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ('http', 'https'):
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or '').casefold()
    if host not in {h.casefold() for h in allowed_hosts}:
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    if port not in (None, 80, 443):
        return False
    if not parsed.path.startswith('/images/I/'):
        return False
    parts = PurePosixPath(parsed.path).parts
    if any(part == '..' for part in parts):
        return False
    if not image_id_from_url(url):
        return False
    return True


def select_main_image(images, allowed_hosts, variant_order):
    """Select the first safe MAIN-image URL in the configured size order.

    Returns a dict with the URLs present, the selected variant/url/id, the
    number of MAIN entries, and a reason. It never falls back to images[0].
    """
    result = {
        'reason': 'no_main_variant', 'variant': '', 'url': '', 'image_id': '',
        'urls': {variant: '' for variant in variant_order}, 'main_count': 0,
    }
    if not isinstance(images, list):
        return result
    mains = [
        entry for entry in images
        if isinstance(entry, dict) and norm(entry.get('variant')) == 'main'
    ]
    result['main_count'] = len(mains)
    if not mains:
        return result
    first_urls = None
    for entry in mains:
        urls = {variant: normalize_url(entry.get(variant)) for variant in variant_order if entry.get(variant)}
        if first_urls is None:
            first_urls = dict(urls)
        for variant in variant_order:
            url = urls.get(variant, '')
            if url and is_safe_image_url(url, allowed_hosts):
                result.update(
                    reason='ok', variant=variant, url=url,
                    image_id=image_id_from_url(url), urls=urls,
                )
                return result
    result['urls'] = first_urls or result['urls']
    result['reason'] = 'no_usable_variant'
    return result


def parse_date_first_available(details):
    """Return (year, year_source, raw_value) from details['Date First Available']."""
    if not isinstance(details, dict):
        return '', 'missing', ''
    raw = details.get('Date First Available')
    if not isinstance(raw, str) or not clean_text(raw):
        return '', 'missing', ''
    raw = clean_text(raw)
    for fmt in DATE_FORMATS:
        try:
            return str(datetime.strptime(raw, fmt).year), 'date_first_available', raw
        except ValueError:
            continue
    match = re.search(r'(?<!\d)((?:19|20)\d{2})(?!\d)', raw)
    if match:
        return match.group(1), 'date_first_available', raw
    return '', 'unparsed', raw


def image_path_for(product_type, item_id):
    shard = hashlib.sha256(item_id.encode('utf-8')).hexdigest()[:2]
    return f'{product_type.casefold()}/{shard}/{item_id}.jpg'


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value):
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def iter_json_records(path):
    """Yield (line_number, parsed_object_or_None, error_text).

    Supports plain JSONL and gzipped JSONL. A gzip file is detected by magic
    bytes, not only by suffix. Malformed lines are yielded with None and an
    error string so callers can count them instead of aborting a long scan.
    """
    path = Path(path)
    with open(path, 'rb') as probe:
        magic = probe.read(2)
    opener = gzip.open if magic == b'\x1f\x8b' else open
    with opener(path, 'rt', encoding='utf-8-sig', errors='replace') as handle:
        for line_number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                yield line_number, json.loads(text), ''
            except Exception as exc:  # malformed line, keep scanning
                yield line_number, None, f'{type(exc).__name__}: {exc}'


class FilterSpec:
    """Pre-normalized category rules loaded from the config file."""

    def __init__(self, config):
        self.root = norm(config['root_category'])
        self.allowed_second = [norm(value) for value in config['second_level_categories']]
        self.allowed_second_set = set(self.allowed_second)
        self.rules = []
        for index, rule in enumerate(config['type_rules'], 1):
            self.rules.append({
                'type': rule['type'],
                'id': rule.get('id') or f'rule_{index}:{rule["type"]}',
                'second_level_any': [norm(value) for value in rule.get('second_level_any', [])],
                'path_contains_any': [norm(value) for value in rule.get('path_contains_any', [])],
                'leaf_contains_any': [norm(value) for value in rule.get('leaf_contains_any', [])],
                'leaf_exclude_any': [norm(value) for value in rule.get('leaf_exclude_any', [])],
            })
        self.fallbacks = {norm(key): value for key, value in config.get('fallbacks', {}).items()}
        self.exclude_segments = [norm(value) for value in config.get('exclude_segments_any', [])]
        self.exclude_leaves = [norm(value) for value in config.get('exclude_leaves_any', [])]
        self.variant_order = tuple(config['images']['variant_order'])
        self.allowed_hosts = tuple(config['images']['allowed_hosts'])


def classify_categories(categories, spec):
    """Return (product_type, reason, category_l2, category_leaf, rule_id)."""
    if not isinstance(categories, list) or not categories:
        return '', 'missing_categories', '', '', ''
    texts = [clean_text(value) for value in categories if clean_text(value)]
    if not texts:
        return '', 'missing_categories', '', '', ''
    if norm(texts[0]) != spec.root:
        return '', 'not_home_and_kitchen', '', '', ''
    if len(texts) < 2:
        return '', 'second_level_out_of_scope', '', clean_text(texts[-1]), ''
    second = norm(texts[1])
    leaf_text = clean_text(texts[-1])
    if second not in spec.allowed_second_set:
        return '', 'second_level_out_of_scope', clean_text(texts[1]), leaf_text, ''
    segments = [tokens(value) for value in texts]
    leaf_tokens = segments[-1]
    if any_phrase_in(segments, spec.exclude_segments) or any_phrase_in([leaf_tokens], spec.exclude_leaves):
        return '', 'excluded_term', clean_text(texts[1]), leaf_text, ''
    for rule in spec.rules:
        if rule['second_level_any'] and second not in rule['second_level_any']:
            continue
        if rule['path_contains_any'] and not any_phrase_in(segments, rule['path_contains_any']):
            continue
        if rule['leaf_contains_any'] and not any_phrase_in([leaf_tokens], rule['leaf_contains_any']):
            continue
        if rule['leaf_exclude_any'] and any_phrase_in([leaf_tokens], rule['leaf_exclude_any']):
            continue
        return rule['type'], '', clean_text(texts[1]), leaf_text, rule['id']
    fallback = spec.fallbacks.get(second)
    if fallback:
        return fallback, '', clean_text(texts[1]), leaf_text, f'fallback:{clean_text(texts[1])}'
    return '', 'type_unmapped', clean_text(texts[1]), leaf_text, ''


def write_json_lf(path, value):
    """Write UTF-8 JSON with LF line endings, stable on Windows."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def write_checksums(out_dir, names):
    """Write checksums.json for existing non-image output files."""
    out_dir = Path(out_dir)
    payload = {}
    for name in names:
        path = out_dir / name
        if path.is_file():
            payload[name] = sha256_file(path)
    write_json_lf(out_dir / 'checksums.json', payload)
    return payload
