# London data and full-query setup

The original London matrix contains **131,596 H3 resolution-10 cells × 1,956 numeric features**. Its December 2025 geographic vectors describe places, buildings, streets, land use and proximity. The complete file is offered under ODbL 1.0; Peter’s source code stays MIT licensed.

## Download and verify

```sh
python tools/fetch_london.py
```

The standard-library fetcher downloads the [original release asset](https://github.com/latintzar/retail-location-similarity/releases/download/london-2025-12-v1/london-res10.parquet) to `data/london-res10.parquet`. It streams into a temporary file, checks both size and SHA-256, then installs the verified file exclusively. An existing different file is preserved.

| Field | Original value |
| --- | --- |
| Size | 56,163,548 bytes |
| SHA-256 | `3e56da16150bc01b7b8a9e84d7d68c85eb76210fc0a0d2916801aafd1dabab5f` |
| Rows | 131,596 |
| Columns | One `h3_index` string plus 1,956 doubles |
| H3 resolution | 10 |
| Retained input release | Overture Maps `2025-12-17.0` |
| Data licence | [ODbL 1.0](../data/london/LICENSE.txt) |

The [manifest](../data/london/manifest.json) and [full ordered schema](../data/london/schema.json) travel with the source. Feature families include 396 count columns, 383 walking estimates, 379 cycling estimates, 373 driving estimates, 373 proximity scores and 52 other geographic measures. Ring-time features estimate distance over the H3 grid using configured speeds; use them as geographic proximity measures.

## Local vector and nearest-match queries

```sh
python location.py embed --lat 51.5117 --lng -0.124 --json
python location.py compare --lat 51.5117 --lng -0.124 --top 100 --json
# Another compatible region:
python location.py compare --cell YOUR_H3_CELL --matrix /path/to/your-matrix.parquet --json
```

`embed` reads the actual named vector. `compare` scans the matrix twice and returns ranked matches. The adapter uses two DuckDB threads, a 256 MB engine memory limit, a 512 MB temporary-file limit and 512-row NumPy batches. Your machine supplies the local CPU, memory and any spill storage. These are explicit local calculations; the default `--preset` path reads the original 34 KB cache immediately.

The reusable `diem_batch.search(..., matrix_path=...)` accepts your local Parquet with `h3_index` and numeric feature columns. Supply the matrix’s coverage, dimensions and data terms alongside that input. The [connections guide](services.md) describes the exact local configuration contract.

### Optional local browser example

```sh
python server.py --local-map
# Enable local full queries after fetching the original matrix:
python server.py --local-map --allow-full-queries
```

This opt-in example binds to loopback. Opening it loads Leaflet/H3 scripts from unpkg and OpenStreetMap tiles. Full-query mode verifies the original matrix hash and adds coordinate/map-cell comparisons. Keep that input read-only while running; changed identity or size/date is rejected before the next calculation. Each search uses a separate spawned process with one concurrent calculation, a 180-second wall timeout, a 120-second CPU allowance and a 2 GiB address-space ceiling. Worker limits use Unix resource controls on Linux/macOS.

These limits are ceilings; a machine or dataset requiring more resources can return a calculation error. The historic recovery measured about 74 seconds and 500 MB RSS for one full search; this is retained evidence from that environment. There is no hosted map preview in the current distribution contract.

## Recompute the three presets

```sh
python tools/precompute_london.py --matrix data/london-res10.parquet
```

This manual tool verifies the exact file and computes Covent Garden, Shoreditch and Soho together in two scans. It writes `data/london/presets-recomputed.json`, preserving the checked shipped cache. It uses the same global minima/maxima, numeric column order, score equations, 15-ring exclusion and average percentile ranking. Review any numerical differences before publishing a replacement cache and its manifest hash.

The shipped [presets](../data/london/presets.json) each retain 100 ranked matches, the full source dimensions and the exact matrix hash. CLI exports add the data licence, attribution, complete-file offer and source notices alongside those unchanged results. The original precomputation was recorded at 80.15 seconds. A fresh packaging review checked their hashes, H3 membership, exclusion, score order and finiteness; it also verified equivalence between the historical pure equations and the independent scorer on bounded cases including 1,956 dimensions. Full cached scores were retained from the original calculation.

## Provenance and reached stage

The complete Parquet was recovered from Peter’s December 2025 Mac checkout; the recovered copy matches its original SHA-256. A dated 23 December build report records the same row/column count and approximately 54 MB output. The file’s schema contains the spatial ID and numerical aggregates; its Parquet key/value metadata is empty.

The retained [ETL source](https://github.com/latintzar/geospatial-agent/blob/194ed2ec8945741eb0e6b4c384be5794fb24fc42/backend/etl/global/build_global_matrix.py) sets Overture release `2025-12-17.0` and reads Places, Base land use/water, Buildings and Transportation. The output’s feature families are consistent with that pipeline. The exact executed revision, configuration and per-record supplier IDs were not embedded in the output. Some retained orchestration and builder revisions differ, so the source is an engineering record rather than a promise of a byte-identical ETL replay.

The achieved result is the original London matrix and functioning comparison. Res8/res5 outputs were recorded during recovery on the Mac; this package distributes the independently checked res10 output. Global build code and estimates survive; completed global output remains unverified.

## Data terms and attribution

**© OpenStreetMap contributors, Overture Maps Foundation.** The London geographic feature matrix is available under the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/). The full machine-readable [matrix download](https://github.com/latintzar/retail-location-similarity/releases/download/london-2025-12-v1/london-res10.parquet) is offered alongside the distributed original results.

The contemporaneous [17 December 2025 attribution document](https://github.com/OvertureMaps/docs/blob/c9b6a5630019536b1a58ac09bac839ef0ce7ec9c/docs/attribution.mdx) identifies ODbL for Base, Buildings and Transportation. Places contributors use CDLA Permissive 2.0, Apache 2.0 and CC0. The exact four-theme notices are retained in [NOTICES.md](../data/london/NOTICES.md), with [all licence texts](../data/london/licenses/README.md). They are a conservative theme-level superset; supplier presence within individual London features is unknown.

The original Overture attribution document’s ETOPO/GLOBathy descriptions and links are preserved verbatim. The [December 2025 Places guide](https://github.com/OvertureMaps/docs/blob/c9b6a5630019536b1a58ac09bac839ef0ce7ec9c/docs/guides/places.mdx) records the source mix for that release. Overture’s current release-retention policy concerns availability from its own buckets; the source data date remains explicit in this historical derivative.

## Verification

```sh
python -m unittest discover -s tests -v
```

Checks exercise all three exact retained API results, prevent full computation in preset mode, reject unavailable/malformed requests, run the synthetic fixture through the actual bounded scorer, enforce the shipped-file boundary and test download checksum/size/race failures while preserving existing files. The 90-record synthetic matrix remains an explicitly named fixture:

```sh
python server.py --local-map --dataset synthetic
```
