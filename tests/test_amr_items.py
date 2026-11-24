"""Safeguards for the Amazon Reviews 2023 Home & Kitchen source-items builder."""
import csv
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'data' / 'Amazon2023'))
sys.path.insert(0, str(ROOT / 'src' / 'negatives'))

import amr_io
import build_amr_items
import verify_amr


def load_config():
    return json.loads((ROOT / 'configs' / 'amr_home_v1.json').read_text(encoding='utf-8'))


def classify(path):
    spec = amr_io.FilterSpec(load_config())
    return amr_io.classify_categories(path, spec)


def record(index, type_index, item_index, categories, with_main=True, title=None, parent_asin=None):
    item_id = parent_asin or f'B{type_index:02d}{item_index:07d}'
    image_id = f'I{type_index:02d}{item_index:07d}'
    image = {
        'large': f'https://m.media-amazon.com/images/I/{image_id}._AC_.jpg',
        'hi_res': f'https://m.media-amazon.com/images/I/{image_id}._AC_SL1500_.jpg',
        'thumb': f'https://m.media-amazon.com/images/I/{image_id}._AC_US75_.jpg',
        'variant': 'MAIN' if with_main else 'PT01',
    }
    return {
        'parent_asin': item_id,
        'title': title if title is not None else f'test product {type_index}-{item_index}',
        'categories': categories,
        'images': [image],
        'details': {
            'Color': 'Blue',
            'Material': 'Wood',
            'Date First Available': 'November 28, 2017',
        },
        'rating_number': 5,
        'average_rating': 4.5,
        'price': 19.99,
        'store': 'Test Store',
        'main_category': 'Amazon Home',
    }


TYPE_CASES = [
    ('CHAIR', ['Home & Kitchen', 'Furniture', 'Living Room Furniture', 'Chairs']),
    ('RUG', ['Home & Kitchen', 'Home Décor Products', 'Rugs, Pads & Protectors', 'Area Rugs']),
    ('TABLE', ['Home & Kitchen', 'Furniture', 'Living Room Furniture', 'Tables', 'End Tables']),
    ('WALL_ART', ['Home & Kitchen', 'Wall Art', 'Posters & Prints']),
    ('SOFA', ['Home & Kitchen', 'Furniture', 'Living Room Furniture', 'Sofas & Couches']),
    ('HOME_FURNITURE_AND_DECOR', ['Home & Kitchen', 'Furniture', 'Bedroom Furniture', 'Beds, Frames & Bases', 'Beds']),
    ('STOOL_SEATING', ['Home & Kitchen', 'Furniture', 'Home Bar Furniture', 'Barstools']),
    ('OTTOMAN', ['Home & Kitchen', 'Furniture', 'Living Room Furniture', 'Ottomans']),
    ('PILLOW', ['Home & Kitchen', 'Bedding', 'Decorative Pillows, Inserts & Covers', 'Throw Pillow Covers']),
    ('HOME', ['Home & Kitchen', 'Home Décor Products', 'Candles & Holders', 'Candles']),
]


def write_fixture(path, reversed_order=False, include_bad=True):
    records = []
    for type_index, (_, categories) in enumerate(TYPE_CASES):
        for item_index in range(3):
            records.append(record(type_index, type_index, item_index, categories))
    if include_bad:
        records.append(record(98, 0, 1, ['Home & Kitchen', 'Furniture', 'Living Room Furniture', 'Chairs'],
                              with_main=False, parent_asin='B990000001'))
        records.append(record(99, 1, 2, ['Home & Kitchen', 'Kitchen & Dining', 'Kitchen & Table Linens', 'Tablecloths'],
                              parent_asin='B990000002'))
        records.append(record(97, 2, 3, ['Home & Kitchen', 'Furniture', 'Living Room Furniture', 'Chairs'],
                              title='', parent_asin='B990000003'))
        records.append(records[0])
    if reversed_order:
        records.reverse()
    path = Path(path)
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        for item in records:
            handle.write(json.dumps(item, ensure_ascii=False) + '\n')
        if include_bad:
            handle.write('{not valid json\n')
    return path


def write_abo_fixture(directory, records):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for suffix in '0123456789abcdef':
        path = directory / f'listings_{suffix}.json.gz'
        with gzip.open(path, 'wt', encoding='utf-8', newline='\n') as handle:
            if suffix == '0':
                for record_value in records:
                    handle.write(json.dumps(record_value, ensure_ascii=False) + '\n')
    return directory


def write_config(path, fixture, max_per_type=2, abo_overlap=None):
    config = load_config()
    config['source']['path'] = str(fixture)
    config['max_per_type'] = max_per_type
    config['abo_overlap'] = {'enabled': False} if abo_overlap is None else abo_overlap
    Path(path).write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def run_builder(fixture, out_dir, config_path, extra=None):
    argv = [
        '--config', str(config_path),
        '--meta-jsonl', str(fixture),
        '--out-dir', str(out_dir),
        '--max-per-type', '2',
        '--skip-source-hash',
    ]
    if extra:
        argv.extend(extra)
    return build_amr_items.main(argv)


def read_rows(path):
    with open(path, encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


class ClassificationTests(unittest.TestCase):
    def test_all_ten_types(self):
        for product_type, path in TYPE_CASES:
            actual, reason, _, _, _ = classify(path)
            self.assertEqual(actual, product_type, (path, reason))

    def test_token_phrase_false_positive(self):
        actual, reason, _, _, _ = classify(
            ['Home & Kitchen', 'Home Décor Products', 'Artificial Plants & Flowers', 'Artificial Vegetables']
        )
        self.assertEqual(actual, 'HOME', reason)

    def test_folding_tables_are_tables_not_chairs(self):
        actual, _, _, _, _ = classify(
            ['Home & Kitchen', 'Furniture', 'Game & Recreation Room Furniture',
             'Folding Tables & Chairs', 'Folding Tables']
        )
        self.assertEqual(actual, 'TABLE')

    def test_table_and_chair_sets_fall_back_to_catch_all(self):
        actual, _, _, _, _ = classify(
            ['Home & Kitchen', 'Furniture', 'Dining Room Furniture', 'Table & Chair Sets']
        )
        self.assertEqual(actual, 'HOME_FURNITURE_AND_DECOR')

    def test_excluded_and_unmapped(self):
        cases = {
            ('Home & Kitchen', 'Furniture', 'Living Room Furniture', 'Slipcovers'): 'excluded_term',
            ('Home & Kitchen', 'Home Décor Products', 'Photo Albums, Frames & Accessories', 'Picture Frames', 'Wall & Tabletop Frames'): '',
            ('Home & Kitchen', 'Bedding', 'Bed Pillows & Positioners', 'Bed Pillows'): 'type_unmapped',
            ('Home & Kitchen', 'Bedding', 'Sheets & Pillowcases', 'Sheets'): 'type_unmapped',
            ('Home & Kitchen', 'Kitchen & Dining', 'Kitchen & Table Linens', 'Tablecloths'): 'second_level_out_of_scope',
        }
        for path, expected_reason in cases.items():
            actual, reason, _, _, _ = classify(list(path))
            if expected_reason:
                self.assertEqual(actual, '', path)
                self.assertEqual(reason, expected_reason, path)
            else:
                self.assertEqual(actual, 'HOME', path)

    def test_pillow_and_bed_pillow(self):
        pillow, _, _, _, _ = classify(
            ['Home & Kitchen', 'Bedding', 'Decorative Pillows, Inserts & Covers', 'Throw Pillows']
        )
        self.assertEqual(pillow, 'PILLOW')
        bed, reason, _, _, _ = classify(
            ['Home & Kitchen', 'Bedding', 'Bed Pillows & Positioners', 'Bed Pillows']
        )
        self.assertEqual(bed, '')
        self.assertEqual(reason, 'type_unmapped')

    def test_home_decor_paths(self):
        for path in [
            ['Home & Kitchen', 'Home Décor Products', 'Home Décor Accents', 'Floating Shelves'],
            ['Home & Kitchen', 'Home Décor Products', 'Mirrors', 'Wall-Mounted Mirrors'],
            ['Home & Kitchen', 'Home Décor Products', 'Window Treatments', 'Curtains & Drapes'],
        ]:
            actual, reason, _, _, _ = classify(path)
            self.assertEqual(actual, 'HOME', (path, reason))


class FieldTests(unittest.TestCase):
    def test_year_parsing(self):
        self.assertEqual(amr_io.parse_date_first_available({'Date First Available': 'November 28, 2017'})[:2], ('2017', 'date_first_available'))
        self.assertEqual(amr_io.parse_date_first_available({'Date First Available': '2019-05-01'})[:2], ('2019', 'date_first_available'))
        self.assertEqual(amr_io.parse_date_first_available({})[:2], ('', 'missing'))
        self.assertEqual(amr_io.parse_date_first_available({'Date First Available': 'unknown'})[:2], ('', 'unparsed'))

    def test_main_image_selection_and_fallback(self):
        spec = amr_io.FilterSpec(load_config())
        images = [
            {'variant': 'PT01', 'large': 'https://m.media-amazon.com/images/I/PT01._AC_.jpg'},
            {'variant': 'MAIN', 'large': 'https://m.media-amazon.com/images/I/MAIN._AC_.jpg'},
        ]
        selected = amr_io.select_main_image(images, spec.allowed_hosts, spec.variant_order)
        self.assertEqual(selected['reason'], 'ok')
        self.assertEqual(selected['variant'], 'large')
        self.assertEqual(selected['image_id'], 'MAIN')

        no_main = amr_io.select_main_image([{'variant': 'PT01', 'large': 'https://m.media-amazon.com/images/I/X._AC_.jpg'}], spec.allowed_hosts, spec.variant_order)
        self.assertEqual(no_main['reason'], 'no_main_variant')

        fallback = amr_io.select_main_image([
            {'variant': 'MAIN', 'large': 'https://evil.example/images/I/X._AC_.jpg',
             'hi_res': 'https://m.media-amazon.com/images/I/Y._AC_SL1500_.jpg'}
        ], spec.allowed_hosts, spec.variant_order)
        self.assertEqual(fallback['reason'], 'ok')
        self.assertEqual(fallback['variant'], 'hi_res')

    def test_image_path_and_safe_id(self):
        self.assertEqual(amr_io.image_path_for('CHAIR', 'B000000001')[:6], 'chair/')
        self.assertTrue(amr_io.image_path_for('CHAIR', 'B000000001').endswith('/B000000001.jpg'))
        self.assertTrue(amr_io.safe_item_id('B000000001'))
        self.assertFalse(amr_io.safe_item_id('../B000000001'))


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.fixture = write_fixture(self.root / 'meta.jsonl')
        self.config = write_config(self.root / 'config.json', self.fixture)

    def tearDown(self):
        self.temp.cleanup()

    def test_build_counts_and_outputs(self):
        out = self.root / 'out'
        self.assertEqual(run_builder(self.fixture, out, self.config), 0)
        items = read_rows(out / 'items.csv')
        self.assertEqual(len(items), 20)
        self.assertEqual(len({row['item_id'] for row in items}), 20)
        self.assertEqual({row['product_type'] for row in items}, {name for name, _ in TYPE_CASES})
        self.assertTrue(all(row['split'] == 'unassigned' for row in items))
        self.assertTrue(all(row['year'] == '2017' for row in items))
        self.assertTrue((out / 'validation.json').is_file())
        self.assertEqual(json.loads((out / 'validation.json').read_text())['status'],
                         'STRUCTURAL_CHECKS_PASSED_INTERMEDIATE_SOURCE_ITEMS')
        manifest = json.loads((out / 'manifest.json').read_text())
        self.assertEqual(manifest['counts']['selected'], 20)
        self.assertEqual(sum(manifest['counts']['by_type_selected'].values()), 20)
        self.assertTrue(manifest['source']['sha256_skipped'])
        self.assertTrue((out / 'no_main_images.csv').is_file())
        self.assertTrue((out / 'checksums.json').is_file())
        exclusions = {row['reason']: int(row['count']) for row in read_rows(out / 'exclusion_summary.csv')}
        self.assertGreaterEqual(exclusions['malformed_json'], 1)
        self.assertGreaterEqual(exclusions['no_main_image'], 1)
        self.assertGreaterEqual(exclusions['second_level_out_of_scope'], 1)
        verified = verify_amr.verify(out, load_config(), check_images=False)
        self.assertEqual(verified['status'], 'STRUCTURAL_CHECKS_PASSED')

    def test_deterministic_items(self):
        first = self.root / 'first'
        second = self.root / 'second'
        self.assertEqual(run_builder(self.fixture, first, self.config), 0)
        self.assertEqual(run_builder(self.fixture, second, self.config), 0)
        self.assertEqual((first / 'items.csv').read_bytes(), (second / 'items.csv').read_bytes())
        self.assertEqual((first / 'filter_summary.csv').read_bytes(), (second / 'filter_summary.csv').read_bytes())
        self.assertEqual((first / 'sampling_summary.csv').read_bytes(), (second / 'sampling_summary.csv').read_bytes())

    def test_reversed_order_same_items(self):
        reversed_fixture = write_fixture(self.root / 'reversed.jsonl', reversed_order=True)
        reversed_config = write_config(self.root / 'reversed-config.json', reversed_fixture)
        first = self.root / 'forward-out'
        second = self.root / 'reverse-out'
        self.assertEqual(run_builder(self.fixture, first, self.config), 0)
        self.assertEqual(run_builder(reversed_fixture, second, reversed_config), 0)
        first_ids = {row['item_id'] for row in read_rows(first / 'items.csv')}
        second_ids = {row['item_id'] for row in read_rows(second / 'items.csv')}
        self.assertEqual(first_ids, second_ids)

    def test_limit_and_gzip(self):
        gz_path = self.root / 'meta.jsonl.gz'
        with open(self.fixture, 'rb') as source, gzip.open(gz_path, 'wb') as target:
            target.write(source.read())
        gz_config = write_config(self.root / 'gz-config.json', gz_path)
        out = self.root / 'gz-out'
        self.assertEqual(build_amr_items.main([
            '--config', str(gz_config), '--meta-jsonl', str(gz_path),
            '--out-dir', str(out), '--max-per-type', '2', '--limit', '5', '--skip-source-hash',
        ]), 0)
        self.assertEqual(len(read_rows(out / 'items.csv')), 5)

    def test_overwrite_guard_and_dry_run(self):
        out = self.root / 'guard'
        self.assertEqual(run_builder(self.fixture, out, self.config), 0)
        with self.assertRaises(SystemExit):
            run_builder(self.fixture, out, self.config)
        dry = self.root / 'dry'
        self.assertEqual(build_amr_items.main([
            '--config', str(self.config), '--meta-jsonl', str(self.fixture),
            '--out-dir', str(dry), '--max-per-type', '2', '--dry-run', '--skip-source-hash',
        ]), 0)
        self.assertFalse(dry.exists())

    def test_resume_requires_items(self):
        with self.assertRaises(SystemExit):
            build_amr_items.main([
                '--config', str(self.config), '--out-dir', str(self.root / 'missing'),
                '--resume-images',
            ])

    def test_abo_overlap_excludes_item_image_and_title(self):
        categories = ['Home & Kitchen', 'Furniture', 'Living Room Furniture', 'Chairs']
        amr_records = [
            record(0, 0, 0, categories, parent_asin='B000000000'),
            record(0, 0, 1, categories, parent_asin='B000000001'),
            record(0, 0, 2, categories, parent_asin='B000000002',
                   title='Exact overlap title for candidate two'),
            record(0, 0, 3, categories, parent_asin='B000000003', title='safe candidate'),
        ]
        amr_path = self.root / 'overlap-amr.jsonl'
        with open(amr_path, 'w', encoding='utf-8', newline='\n') as handle:
            for item in amr_records:
                handle.write(json.dumps(item, ensure_ascii=False) + '\n')
        abo_dir = write_abo_fixture(self.root / 'abo', [
            {'item_id': 'B000000000', 'main_image_id': 'I999999999', 'other_image_id': [],
             'item_name': [{'language_tag': 'en_US', 'value': 'item overlap'}]},
            {'item_id': 'B999999999', 'main_image_id': 'I000000001', 'other_image_id': [],
             'item_name': [{'language_tag': 'en_US', 'value': 'image overlap'}]},
            {'item_id': 'B888888888', 'main_image_id': 'I888888888', 'other_image_id': [],
             'item_name': [{'language_tag': 'en_US', 'value': 'Exact overlap title for candidate two'}]},
        ])
        config = write_config(
            self.root / 'overlap-config.json', amr_path, max_per_type=3,
            abo_overlap={
                'enabled': True, 'listings_dir': str(abo_dir),
                'exclude_item_ids': True, 'exclude_image_ids': True, 'exclude_exact_titles': True,
            },
        )
        out = self.root / 'overlap-out'
        self.assertEqual(run_builder(amr_path, out, config, extra=['--max-per-type', '3']), 0)
        items = read_rows(out / 'items.csv')
        self.assertEqual([row['item_id'] for row in items], ['B000000003'])
        overlaps = read_rows(out / 'abo_overlap.csv')
        self.assertEqual(len(overlaps), 3)
        self.assertEqual({row['item_id'] for row in overlaps}, {'B000000000', 'B000000001', 'B000000002'})
        signals = {row['item_id']: row['signals'] for row in overlaps}
        self.assertIn('item_id', signals['B000000000'])
        self.assertIn('image_id', signals['B000000001'])
        self.assertIn('title', signals['B000000002'])
        manifest = json.loads((out / 'manifest.json').read_text())
        self.assertEqual(manifest['abo_overlap']['excluded'], 3)
        self.assertEqual(manifest['abo_overlap']['by_signal'], {'image_id': 1, 'item_id': 1, 'title': 1})

    def test_duplicate_parent_asin_selected_once(self):
        out = self.root / 'dupes'
        self.assertEqual(run_builder(self.fixture, out, self.config, extra=['--max-per-type', '10']), 0)
        items = read_rows(out / 'items.csv')
        self.assertEqual(len(items), len({row['item_id'] for row in items}))
        manifest = json.loads((out / 'manifest.json').read_text())
        self.assertGreaterEqual(manifest['counts']['duplicates'], 1)


if __name__ == '__main__':
    unittest.main()
