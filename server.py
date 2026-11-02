"""Loopback map preview: original London presets, with opt-in local matrix search."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import hashlib
import json
import math
import multiprocessing
import os
import threading
import stat

BASE = Path(__file__).resolve().parent
DATA = BASE / 'data' / 'london'
MANIFEST = json.loads((DATA / 'manifest.json').read_text())
CACHE = json.loads((DATA / 'presets.json').read_text())
QUERY_CONTEXT = multiprocessing.get_context('spawn')
if hashlib.sha256((DATA / 'presets.json').read_bytes()).hexdigest() != MANIFEST['preset_cache_sha256']:
    raise RuntimeError('London preset cache checksum mismatch')
for key, entry in CACHE.items():
    if entry['reference']['hex'] != key or entry['cache_provenance']['matrix_sha256'] != MANIFEST['sha256']:
        raise RuntimeError('London preset provenance mismatch')

# Only explicitly shipped public files can be served; matrix downloads use the release asset.
STATIC = {'/': BASE / 'index.html', '/index.html': BASE / 'index.html'}
PUBLIC_NAV = ['atelier-nav.js', 'atelier-nav.css', 'atelier-asterisk.svg', 'atelier-nav-fonts/archivo-variable.woff2']
PUBLIC_DATA = ['manifest.json', 'schema.json', 'presets.json', 'NOTICES.md', 'LICENSE.txt',
               'licenses/ODbL-1.0.txt', 'licenses/CDLA-Permissive-2.0.txt', 'licenses/Apache-2.0.txt',
               'licenses/CC-BY-4.0.txt', 'licenses/CC0-1.0.txt', 'licenses/Overture-docs-MIT.txt']
for prefix, folder, names in [('/native-nav/', BASE / 'native-nav', PUBLIC_NAV), ('/data/london/', DATA, PUBLIC_DATA)]:
    for name in names:
        STATIC[prefix + name] = folder / name
MIME = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
        '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.woff2': 'font/woff2',
        '.json': 'application/json', '.md': 'text/plain; charset=utf-8', '.txt': 'text/plain; charset=utf-8'}


def calculate(pipe, lat, lng, top, matrix):
    """A separate bounded process owns optional full-matrix computation."""
    try:
        os.environ['OPENBLAS_NUM_THREADS'] = '1'
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (120, 121))
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        from diem_batch import search
        pipe.send((True, search(lat, lng, top, matrix_path=matrix)))
    except Exception as error:
        pipe.send((False, str(error)))
    finally:
        pipe.close()


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, *, dataset='london', matrix=None, allow_full_queries=False):
        self.dataset = dataset
        self.matrix = Path(matrix).resolve() if matrix else (BASE / 'synthetic-example.parquet' if dataset == 'synthetic' else BASE / 'data' / 'london-res10.parquet')
        self.allow_full_queries = allow_full_queries or dataset == 'synthetic'
        self.query_lock = threading.Lock()
        self.query_timeout = 180
        if self.allow_full_queries and not self.matrix.is_file():
            raise ValueError('Download a matrix with python tools/fetch_london.py, or supply --matrix PATH')
        if dataset == 'london' and self.allow_full_queries:
            with self.matrix.open('rb') as source:
                if hashlib.file_digest(source, 'sha256').hexdigest() != MANIFEST['sha256']:
                    raise ValueError('London matrix checksum mismatch')
        self.matrix_identity = self.matrix.stat() if self.allow_full_queries else None
        super().__init__(address, handler)

    def source(self):
        real = self.dataset == 'london'
        return {
            'dataset': 'London historical matrix' if real else 'Synthetic test fixture',
            'coverage': 'London · December 2025 · 131,596 H3 resolution-10 cells' if real else '90 generated records around three London references',
            'features': 1956 if real else 5,
            'source': MANIFEST['source_attribution'] if real else 'Deterministically generated feature values',
            'license': 'ODbL-1.0' if real else 'Authored synthetic fixture',
            'license_url': MANIFEST['license_url'] if real else None,
            'data_url': MANIFEST['download_url'] if real else None,
            'notices_url': 'data/london/NOTICES.md' if real else None,
            'manifest_url': 'data/london/manifest.json' if real else None,
            'matrix_sha256': MANIFEST['sha256'] if real else None,
            'method': 'Leo’s historic calibrated distance, inspired by DIEM',
            'full_queries': self.allow_full_queries,
            'result_mode': 'original-matrix-calculation' if self.allow_full_queries and real else 'original-matrix-presets' if real else 'synthetic-calculation',
            'presets': [{'id': key, 'name': entry['cache_provenance']['name'],
                         'lat': entry['reference']['lat'], 'lng': entry['reference']['lng']}
                        for key, entry in CACHE.items()]
        }


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        payload = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/source':
            return self.send_json(self.server.source())
        file = STATIC.get(path)
        if file is None:
            self.send_error(404)
            return
        try:
            resolved = file.resolve(strict=True)
            if not resolved.is_relative_to(BASE) or resolved != file.absolute():
                raise ValueError('Static aliases are not served')
            descriptor = os.open(file, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
            with os.fdopen(descriptor, 'rb') as source:
                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                    raise ValueError('Static path is not a regular file')
                payload = source.read()
        except (OSError, ValueError):
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', MIME.get(file.suffix, 'text/plain; charset=utf-8'))
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if urlsplit(self.path).path != '/api/search':
            self.send_error(404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2048:
                raise ValueError('Invalid request size')
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError('Expected a JSON object')
            top = max(1, min(int(request.get('top_k', 100)), 100))
            preset = request.get('preset')
            if preset is not None:
                if preset not in CACHE:
                    raise ValueError('Choose Covent Garden, Shoreditch or Soho')
                entry = CACHE[preset]
                lat, lng = entry['reference']['lat'], entry['reference']['lng']
            else:
                lat, lng = float(request['lat']), float(request['lng'])
            if not math.isfinite(lat) or not math.isfinite(lng) or not 51 <= lat <= 52 or not -1 <= lng <= 1:
                raise ValueError('Choose a location within London coverage')
            if self.server.dataset == 'london' and not self.server.allow_full_queries:
                if preset is None:
                    # Legacy coordinate clients can request the same three original reference cells.
                    import h3
                    preset = h3.latlng_to_cell(lat, lng, 10)
                entry = CACHE.get(preset)
                if entry is None:
                    return self.send_json({'error': 'Choose one of the three London reference locations', 'available_presets': self.server.source()['presets']}, 422)
                if top != 100:
                    return self.send_json({'error': 'The retained preset contains 100 ranked matches; use top_k=100'}, 422)
                return self.send_json(entry)
            identity = self.server.matrix.stat()
            expected = self.server.matrix_identity
            if (identity.st_dev, identity.st_ino, identity.st_size, identity.st_mtime_ns) != (expected.st_dev, expected.st_ino, expected.st_size, expected.st_mtime_ns):
                raise ValueError('Matrix changed; restart the local server with the reviewed input')
            if not self.server.query_lock.acquire(blocking=False):
                return self.send_json({'error': 'Another comparison is running. Try again shortly.'}, 429)
            parent = child = worker = None
            try:
                parent, child = QUERY_CONTEXT.Pipe(duplex=False)
                worker = QUERY_CONTEXT.Process(target=calculate, args=(child, lat, lng, top, str(self.server.matrix)))
                worker.start()
                child.close()
                if not parent.poll(self.server.query_timeout):
                    raise TimeoutError('Comparison exceeded three minutes')
                ok, result = parent.recv()
                if not ok:
                    raise ValueError(result)
                self.send_json(result)
            finally:
                if worker is not None and worker.pid is not None:
                    worker.join(timeout=1)
                    if worker.is_alive():
                        worker.terminate()
                        worker.join(timeout=2)
                    if worker.is_alive():
                        worker.kill()
                        worker.join()
                if parent is not None:
                    parent.close()
                if child is not None:
                    child.close()
                self.server.query_lock.release()
        except (ValueError, TypeError, KeyError, EOFError, TimeoutError) as error:
            self.send_json({'error': str(error)}, 400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-map', action='store_true', help='Explicitly serve the optional loopback map example')
    parser.add_argument('--dataset', choices=['london', 'synthetic'], default='london')
    parser.add_argument('--matrix', type=Path, help='Local historical London matrix; verified before full queries')
    parser.add_argument('--allow-full-queries', action='store_true', help='Enable bounded local full-matrix calculation')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '18869')))
    args = parser.parse_args()
    if not args.local_map:
        parser.error('Use location.py for the CLI, or --local-map to serve the optional browser example')
    if args.matrix and not args.allow_full_queries:
        parser.error('--matrix requires --allow-full-queries')
    with PreviewServer(('127.0.0.1', args.port), Handler, dataset=args.dataset, matrix=args.matrix, allow_full_queries=args.allow_full_queries) as server:
        print(f'Retail Location Similarity: http://127.0.0.1:{server.server_port} ({server.dataset})', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
