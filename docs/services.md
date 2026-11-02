# Connections and services

The CLI reads local geographic matrices and calculates matches locally. Its supported location inputs are coordinates and H3 cells.

| Connection | Configuration | Execution |
| --- | --- | --- |
| Your geographic matrix | `--matrix PATH`, or `RETAIL_MATRIX_PATH` | Read a local H3 resolution-10 Parquet with numeric features. |
| Original London example | `python tools/fetch_london.py` | Explicitly download the public GitHub release asset and verify its size/hash. |
| Original retained results | `python location.py compare --preset covent-garden` | Read the shipped cache locally using the standard library. |
| Optional browser map | `python server.py --local-map` | Bind loopback; opening the page loads Leaflet/H3 scripts from unpkg and tiles from OpenStreetMap. |

## Provider credentials

Coordinates, H3 indexing, local matrix access and similarity scoring use the local toolchain. The executable source has no Google Maps, Geocoding, Routes, Places or Mapbox integration. Provider credentials are neither loaded nor requested by this setup.

When extending the project with address lookup or another provider, add an explicit connector with your own account, key and usage limits. Keep that connector opt-in and its credentials in a local secret store. The [agent skill](../skills/retail-location-similarity/SKILL.md) preserves the current coordinate/H3 contract.

## Global feature-building source

The separate [Geospatial Agent ETL](https://github.com/latintzar/geospatial-agent/tree/main/backend/etl/global) retains the original wider feature-generation and cloud-launch work. Use it as an engineering reference. Cloud provisioning, third-party model calls and data-provider accounts each require an explicitly configured execution environment; this repository’s setup runs the local comparison path.
