"""The original cache, ordered schema and licence offer remain one coherent package."""
from pathlib import Path
import hashlib
import json
import unittest
import h3

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/london'


class DataPackageTest(unittest.TestCase):
    def test_schema_and_cache_match_the_published_matrix_contract(self):
        manifest = json.loads((DATA / 'manifest.json').read_text())
        schema = json.loads((DATA / 'schema.json').read_text())
        self.assertEqual(schema['matrix_sha256'], manifest['sha256'])
        self.assertEqual(len(schema['column_order']), manifest['columns'])
        self.assertEqual(schema['column_order'][0], {'name': 'h3_index', 'type': 'VARCHAR'})
        self.assertTrue(all(column['type'] == 'DOUBLE' for column in schema['column_order'][1:]))
        cache_bytes = (DATA / 'presets.json').read_bytes()
        self.assertEqual(hashlib.sha256(cache_bytes).hexdigest(), manifest['preset_cache_sha256'])
        cache = json.loads(cache_bytes)
        self.assertEqual(len(cache), 3)
        for key, result in cache.items():
            with self.subTest(reference=key):
                self.assertEqual(result['cache_provenance']['matrix_sha256'], manifest['sha256'])
                self.assertEqual(result['stats']['total_hexes'], manifest['rows'])
                self.assertEqual(result['stats']['feature_dimensions'], manifest['numeric_features'])
                self.assertEqual(len(result['similar_hexes']), 100)
                excluded = set(h3.grid_disk(key, 15))
                self.assertTrue(all(h3.is_valid_cell(row['hex']) and row['hex'] not in excluded for row in result['similar_hexes']))
                scores = [row['similarity'] for row in result['similar_hexes']]
                self.assertEqual(scores, sorted(scores, reverse=True))

    def test_data_offer_and_all_upstream_texts_are_shipped_separately_from_mit(self):
        manifest = json.loads((DATA / 'manifest.json').read_text())
        self.assertEqual(manifest['database_license'], 'ODbL-1.0')
        self.assertTrue(manifest['download_url'].endswith('/london-2025-12-v1/london-res10.parquet'))
        self.assertIn('MIT License', (ROOT / 'LICENSE').read_text())
        for filename in ['ODbL-1.0.txt', 'CDLA-Permissive-2.0.txt', 'Apache-2.0.txt', 'CC-BY-4.0.txt', 'CC0-1.0.txt', 'Overture-docs-MIT.txt']:
            with self.subTest(filename=filename):
                self.assertGreater((DATA / 'licenses' / filename).stat().st_size, 1000)
        notices = (DATA / 'NOTICES.md').read_text()
        for text in ['## Base', '## Buildings', '## Places', '## Transportation', 'Copyright 2024 Foursquare Labs, Inc.']:
            self.assertIn(text, notices)


if __name__ == '__main__':
    unittest.main()
