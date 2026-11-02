"""CLI defaults use original local evidence, with explicit matrix and network actions."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
import json
import os
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import location


class LocationCLITest(unittest.TestCase):
    def invoke(self, args):
        output = StringIO()
        with redirect_stdout(output):
            location.main(args)
        return output.getvalue()

    def test_default_original_result_and_full_json_are_offline(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('CLI preset must remain offline')), patch('socket.socket', side_effect=AssertionError('CLI preset must remain offline')):
            result = json.loads(self.invoke(['compare', '--preset', 'covent-garden', '--json']))
            self.assertEqual(len(result['similar_hexes']), 100)
            self.assertEqual(result['stats']['feature_dimensions'], 1956)
            self.assertEqual(result['data_source']['database_license'], 'ODbL-1.0')
            self.assertIn('/releases/download/', result['data_source']['complete_database_url'])
            self.assertEqual(result['cache_provenance']['matrix_sha256'], '3e56da16150bc01b7b8a9e84d7d68c85eb76210fc0a0d2916801aafd1dabab5f')
            self.assertIn('shoreditch', self.invoke(['examples']))

    def test_embedding_reads_the_real_named_values_from_explicit_local_fixture(self):
        fixture = location.ROOT / 'synthetic-example.parquet'
        result = json.loads(self.invoke(['embed', '--lat', '51.5117', '--lng', '-0.124', '--matrix', str(fixture), '--json']))
        self.assertEqual(result['dimensions'], 5)
        self.assertEqual(len(result['features']), 5)
        self.assertEqual(result['location']['hex'], '8a194ad324f7fff')

    def test_explicit_matrix_comparison_runs_the_scorer(self):
        fixture = location.ROOT / 'synthetic-example.parquet'
        result = json.loads(self.invoke(['compare', '--cell', '8a194ad324f7fff', '--matrix', str(fixture), '--top', '5', '--json']))
        self.assertEqual(result['stats']['total_hexes'], 90)
        self.assertEqual(len(result['similar_hexes']), 5)

    def test_matrix_environment_connector_selects_only_the_named_local_file(self):
        fixture = location.ROOT / 'synthetic-example.parquet'
        with patch.dict(os.environ, {'RETAIL_MATRIX_PATH': str(fixture)}):
            self.assertEqual(location.matrix_path(None), fixture)
        with self.assertRaises(ValueError):
            location.matrix_path('/missing/own-matrix.parquet')


if __name__ == '__main__':
    unittest.main()
