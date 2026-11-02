"""Actual retained results, opt-in scorer, and the public-file boundary over loopback."""
from contextlib import contextmanager
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import hashlib
import json
import sys
import threading
import tempfile
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class QuietHandler(server.Handler):
    def log_message(self, *args):
        pass


@contextmanager
def preview(**options):
    http = server.PreviewServer(('127.0.0.1', 0), QuietHandler, **options)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        yield 'http://127.0.0.1:' + str(http.server_port)
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=5)


def post(origin, body):
    if isinstance(body, dict):
        body = json.dumps(body).encode()
    request = urllib.request.Request(origin + '/api/search', data=body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


class ScorerHTTPTest(unittest.TestCase):
    def test_all_three_original_presets_return_exact_retained_results_without_a_worker(self):
        with preview() as origin, patch.object(server.QUERY_CONTEXT, 'Process', side_effect=AssertionError('presets must stay cheap')):
            for key, expected in server.CACHE.items():
                with self.subTest(preset=key):
                    status, result = post(origin, {'preset': key})
                    self.assertEqual(status, 200)
                    self.assertEqual(result, expected)
                    self.assertEqual(len(result['similar_hexes']), 100)
                    self.assertEqual(result['stats']['total_hexes'], 131596)
                    self.assertEqual(result['stats']['feature_dimensions'], 1956)
                    self.assertEqual(result['cache_provenance']['matrix_sha256'], server.MANIFEST['sha256'])

    def test_unknown_coordinates_have_an_explicit_real_preset_response(self):
        with preview() as origin:
            status, result = post(origin, {'lat': 51.6, 'lng': 0.2})
            self.assertEqual(status, 422)
            self.assertEqual(len(result['available_presets']), 3)
            self.assertNotIn('similar_hexes', result)
            self.assertEqual(post(origin, {'preset': '8a194ad324f7fff', 'top_k': 5})[0], 422)

    def test_synthetic_fixture_still_runs_the_actual_scorer_explicitly(self):
        with preview(dataset='synthetic') as origin:
            status, result = post(origin, {'lat': 51.5117, 'lng': -.124, 'top_k': 5})
            self.assertEqual(status, 200, result)
            self.assertEqual(len(result['similar_hexes']), 5)
            self.assertEqual(result['stats']['total_hexes'], 90)
            self.assertEqual(result['stats']['feature_dimensions'], 5)
            scores = [row['similarity'] for row in result['similar_hexes']]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_invalid_requests_are_rejected_before_search(self):
        with preview() as origin:
            for body in [b'{', b'x' * 2049, b'[]', {'lat': 0, 'lng': 0}, {'lat': float('inf'), 'lng': 0}, {'preset': 'unknown'}]:
                with self.subTest(body=str(body)[:50]):
                    self.assertEqual(post(origin, body)[0], 400)

    def test_source_identifies_actual_file_and_public_files_are_allowlisted(self):
        with preview() as origin:
            with urllib.request.urlopen(origin + '/api/source', timeout=5) as response:
                source = json.load(response)
            self.assertEqual(source['features'], 1956)
            self.assertEqual(source['matrix_sha256'], server.MANIFEST['sha256'])
            self.assertEqual(source['result_mode'], 'original-matrix-presets')
            self.assertFalse(source['full_queries'])
            self.assertIn('/releases/download/', source['data_url'])
            for path, mime in [('native-nav/atelier-nav.js', 'javascript'), ('native-nav/atelier-nav-fonts/archivo-variable.woff2', 'font/woff2'), ('data/london/NOTICES.md', 'text/plain'), ('data/london/schema.json', 'application/json')]:
                with self.subTest(path=path), urllib.request.urlopen(origin + '/' + path, timeout=5) as response:
                    self.assertIn(mime, response.headers['Content-Type'])
                    self.assertGreater(len(response.read()), 0)
            for path in ['server.py', '.env', 'data/london/../../server.py', 'data/london/.env', 'native-nav/atelier-nav-fonts/Archivo-OFL.txt.private', 'data/london-res10.parquet']:
                with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(origin + '/' + path, timeout=5)
                self.assertEqual(error.exception.code, 404)

    def test_allowlisted_static_alias_cannot_expose_an_outside_file(self):
        with tempfile.TemporaryDirectory(dir=server.BASE) as public_directory, tempfile.TemporaryDirectory() as private_directory:
            private_file = Path(private_directory) / 'private.txt'
            private_file.write_bytes(b'private owner record')
            alias = Path(public_directory) / 'notice.txt'
            alias.symlink_to(private_file)
            with patch.dict(server.STATIC, {'/test-allowed-notice.txt': alias}), preview() as origin:
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(origin + '/test-allowed-notice.txt', timeout=5)
                self.assertEqual(error.exception.code, 404)
                self.assertNotIn(b'private owner record', error.exception.read())

    def test_replaced_full_query_matrix_is_rejected_before_starting_a_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            matrix = Path(directory) / 'matrix.parquet'
            matrix.write_bytes((server.BASE / 'synthetic-example.parquet').read_bytes())
            with preview(dataset='synthetic', matrix=matrix) as origin, patch.object(server.QUERY_CONTEXT, 'Process', side_effect=AssertionError('changed input must be rejected')):
                replacement = Path(directory) / 'replacement.parquet'
                replacement.write_bytes(matrix.read_bytes())
                replacement.replace(matrix)
                status, result = post(origin, {'lat': 51.5117, 'lng': -.124})
                self.assertEqual(status, 400)
                self.assertIn('Matrix changed', result['error'])

    def test_london_full_queries_require_the_exact_matrix(self):
        with self.assertRaises(ValueError):
            server.PreviewServer(('127.0.0.1', 0), QuietHandler, matrix=server.BASE / 'synthetic-example.parquet', allow_full_queries=True)


if __name__ == '__main__':
    unittest.main()
