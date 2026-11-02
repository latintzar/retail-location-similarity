"""Two-pass matrix adapter for Leo’s independently expressed historical equations."""
from pathlib import Path
import warnings
import duckdb
import h3
import numpy as np
from _scoring import compute_diem

MATRIX = Path(__file__).resolve().parent / 'synthetic-example.parquet'
NUMERIC = ('TINYINT', 'SMALLINT', 'INTEGER', 'BIGINT', 'HUGEINT', 'UTINYINT',
           'USMALLINT', 'UINTEGER', 'UBIGINT', 'FLOAT', 'DOUBLE', 'DECIMAL')


def search(lat, lng, top_k=100, batch_size=512, *, matrix_path=None):
    """Compare the reference against a Parquet's numeric features in two scans.

    ``matrix_path`` accepts your own attributed H3 feature matrix. The default
    is the small authored fixture; the HTTP server passes its selected matrix.
    """
    path = str(matrix_path or MATRIX)
    with duckdb.connect() as db:
        db.execute('SET threads=2')
        db.execute("SET memory_limit='256MB'")
        db.execute("SET max_temp_directory_size='512MB'")
        schema = db.execute('DESCRIBE SELECT * FROM read_parquet(?)', [path]).fetchall()
        cols = [row[0] for row in schema if row[0] != 'h3_index' and row[1].startswith(NUMERIC)]
        if not cols:
            raise ValueError('No numeric features in matrix')
        quoted = ','.join('"' + name.replace('"', '""') + '"' for name in cols)
        query = 'SELECT h3_index,' + quoted + ' FROM read_parquet(?)'
        ref_hex = h3.latlng_to_cell(lat, lng, 10)
        reference = None
        minimum, maximum = np.full(len(cols), np.inf), np.full(len(cols), -np.inf)
        cursor = db.execute(query, [path])
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='All-NaN slice encountered')
            while rows := cursor.fetchmany(batch_size):
                values = np.asarray([row[1:] for row in rows], dtype=np.float64)
                minimum = np.fmin(minimum, np.nanmin(values, axis=0))
                maximum = np.fmax(maximum, np.nanmax(values, axis=0))
                for index, row in enumerate(rows):
                    if row[0] == ref_hex:
                        reference = values[index].copy()
        if reference is None:
            raise ValueError('Selected location is outside the supplied matrix')
        minimum[np.isinf(minimum)] = np.nan
        maximum[np.isinf(maximum)] = np.nan
        excluded = set(h3.grid_disk(ref_hex, 15))
        results = []
        total, sum_scores = 0, 0.0
        cursor = db.execute(query, [path])
        while rows := cursor.fetchmany(batch_size):
            values = np.asarray([row[1:] for row in rows], dtype=np.float64)
            scores = compute_diem(reference, values, minimum, maximum)
            total += len(scores)
            sum_scores += float(scores.sum())
            results.extend((row[0], float(score)) for row, score in zip(rows, scores) if row[0] not in excluded)
    results.sort(key=lambda item: item[1], reverse=True)
    results = results[:max(1, min(top_k, 1000))]
    # Preserve the original pandas rank(pct=True), including average rank for ties.
    values = np.array([item[1] for item in results])
    ranks = np.empty(len(values))
    order = np.argsort(values, kind='stable')
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        ranks[order[index:end]] = (index + 1 + end) / (2 * len(values))
        index = end
    matches = [{'hex': cell, 'similarity': score, 'percentile': float(rank * 100),
                'value': float(rank**2.5 * 100)} for (cell, score), rank in zip(results, ranks)]
    ref_lat, ref_lng = h3.cell_to_latlng(ref_hex)
    return {
        'reference': {'hex': ref_hex, 'lat': ref_lat, 'lng': ref_lng, 'description': None,
                      'starter_pack': None, 'top_scores': []},
        'similar_hexes': matches,
        'stats': {'total_hexes': total, 'feature_dimensions': len(cols), 'top_k': top_k,
                  'mean_similarity': sum_scores / total,
                  'max_similarity': results[0][1] if results else 0,
                  'min_similarity': results[-1][1] if results else 0}
    }
