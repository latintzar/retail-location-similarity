#!/usr/bin/env python3
"""Geographic feature vectors and nearest-location comparisons, computed locally."""
from pathlib import Path
import argparse
import json
import hashlib
import math
import os

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data/london'
MANIFEST = json.loads((DATA / 'manifest.json').read_text())
PRESET_BYTES = (DATA / 'presets.json').read_bytes()
if hashlib.sha256(PRESET_BYTES).hexdigest() != MANIFEST['preset_cache_sha256']:
    raise RuntimeError('London preset cache checksum mismatch')
PRESETS = json.loads(PRESET_BYTES)
PRESET_NAMES = {entry['cache_provenance']['name'].lower().replace(' ', '-'): key for key, entry in PRESETS.items()}


def matrix_path(value):
    path = Path(value or os.environ.get('RETAIL_MATRIX_PATH', ROOT / 'data/london-res10.parquet')).expanduser().resolve()
    if not path.is_file():
        raise ValueError('Supply --matrix PATH, or run python tools/fetch_london.py for the original London example')
    return path


def coordinates(args):
    import h3
    if args.cell:
        if args.lat is not None or args.lng is not None:
            raise ValueError('Choose --cell, or --lat and --lng')
        if not h3.is_valid_cell(args.cell) or h3.get_resolution(args.cell) != 10:
            raise ValueError('Supply an H3 resolution-10 cell')
        return h3.cell_to_latlng(args.cell)
    if args.lat is None or args.lng is None or not math.isfinite(args.lat) or not math.isfinite(args.lng) or not -90 <= args.lat <= 90 or not -180 <= args.lng <= 180:
        raise ValueError('Supply --lat and --lng, or --cell H3_ID')
    return args.lat, args.lng


def embedding(lat, lng, matrix):
    """Read one actual H3 feature vector from your local matrix, preserving schema order."""
    import duckdb
    import h3
    from diem_batch import NUMERIC
    cell = h3.latlng_to_cell(lat, lng, 10)
    with duckdb.connect() as db:
        db.execute('SET threads=2')
        db.execute("SET memory_limit='256MB'")
        db.execute("SET max_temp_directory_size='512MB'")
        schema = db.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(matrix)]).fetchall()
        names = [row[0] for row in schema if row[0] != 'h3_index' and row[1].startswith(NUMERIC)]
        if not names:
            raise ValueError('Matrix needs h3_index and numeric feature columns')
        columns = ','.join('"' + name.replace('"', '""') + '"' for name in names)
        row = db.execute('SELECT ' + columns + ' FROM read_parquet(?) WHERE h3_index=? LIMIT 1', [str(matrix), cell]).fetchone()
    if row is None:
        raise ValueError('Selected location is outside the supplied matrix')
    values = [None if value is None or not math.isfinite(float(value)) else float(value) for value in row]
    return {'location': {'hex': cell, 'lat': lat, 'lng': lng}, 'dimensions': len(names),
            'features': dict(zip(names, values)), 'method': 'Designed geographic feature vector'}


def original_data_source():
    return {'name': MANIFEST['name'], 'source_release': MANIFEST['release'],
            'matrix_sha256': MANIFEST['sha256'], 'database_license': MANIFEST['database_license'],
            'attribution': MANIFEST['source_attribution'], 'license_url': MANIFEST['license_url'],
            'complete_database_url': MANIFEST['download_url'],
            'source_notices_url': 'https://github.com/latintzar/retail-location-similarity/blob/main/data/london/NOTICES.md',
            'provenance': MANIFEST['provenance']}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest='command', required=True)
    commands.add_parser('examples', help='List the three retained original London calculations')
    for name in ['embed', 'compare']:
        sub = commands.add_parser(name)
        sub.add_argument('--lat', type=float)
        sub.add_argument('--lng', type=float)
        sub.add_argument('--cell', help='H3 resolution-10 identifier')
        sub.add_argument('--matrix', help='Your local Parquet with H3 IDs and numerical features')
        sub.add_argument('--json', action='store_true', help='Print the complete machine-readable result')
        if name == 'compare':
            sub.add_argument('--preset', choices=list(PRESET_NAMES), help='Read a retained full-matrix result immediately')
            sub.add_argument('--top', type=int, default=100)
    return result


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.command == 'examples':
            for name, key in PRESET_NAMES.items():
                print(f'{name}\t{key}\t100 matches · 131,596 cells · 1,956 features')
            return
        if args.command == 'compare' and args.preset:
            if args.cell or args.lat is not None or args.lng is not None or args.matrix:
                raise ValueError('Choose --preset alone, or supply your location and matrix')
            if args.top != 100:
                raise ValueError('The original preset retains 100 ranked matches; use --top 100')
            output = dict(PRESETS[PRESET_NAMES[args.preset]])
            output['data_source'] = original_data_source()
        else:
            lat, lng = coordinates(args)
            path = matrix_path(args.matrix)
            if args.command == 'embed':
                output = embedding(lat, lng, path)
            else:
                if not 1 <= args.top <= 1000:
                    raise ValueError('--top must be between 1 and 1000')
                from diem_batch import search
                output = search(lat, lng, args.top, matrix_path=path)
            if path.stat().st_size == MANIFEST['bytes']:
                with path.open('rb') as source:
                    if hashlib.file_digest(source, 'sha256').hexdigest() == MANIFEST['sha256']:
                        output['data_source'] = original_data_source()
        if args.json:
            print(json.dumps(output, indent=2, allow_nan=False))
        elif args.command == 'embed':
            print(f'Location: {output["location"]["hex"]}\nDimensions: {output["dimensions"]}')
            for name, value in list(output['features'].items())[:8]:
                print(f'{name}: {value}')
            print('Use --json for the complete ordered feature vector.')
        else:
            name = output.get('cache_provenance', {}).get('name', output['reference']['hex'])
            print(f'Reference: {name}\nCompared cells: {output["stats"]["total_hexes"]:,}\nFeatures: {output["stats"]["feature_dimensions"]:,}\nMatches: {len(output["similar_hexes"])}')
            for index, match in enumerate(output['similar_hexes'][:5], 1):
                print(f'{index}. {match["hex"]}  {match["similarity"]:.6f}')
            print('Use --json for all matches, scores and source provenance.')
        if not args.json and 'data_source' in output:
            print('Data: © OpenStreetMap contributors, Overture Maps Foundation · ODbL 1.0')
            print('Complete data: ' + output['data_source']['complete_database_url'])
    except (OSError, ValueError, ImportError) as error:
        cli.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
