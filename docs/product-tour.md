# Product tour

Retail Location Similarity compares geographic feature vectors to find locations like a reference retail site. A location becomes an H3 cell; its numerical context is compared with other cells in your matrix. You choose the reference using your own business knowledge.

[Run locally](../README.md#run-locally) · [Data and setup](london-data.md) · [Agent skill](../skills/retail-location-similarity/SKILL.md)

## Location, embedding, matches

1. Start with an actual retained comparison:

   ```sh
   python location.py compare --preset covent-garden --json > matches.json
   ```

   The file contains 100 original matches calculated across 131,596 London H3 cells and 1,956 features, with the source matrix’s exact SHA-256. Shoreditch and Soho are the other two verified examples.

2. Install the local numerical dependencies and explicitly download the original matrix:

   ```sh
   pip install -r requirements.txt
   python tools/fetch_london.py
   ```

3. Read a location’s actual geographic vector:

   ```sh
   python location.py embed --lat 51.5117 --lng -0.124 --json > vector.json
   ```

   The result identifies its H3 cell, dimension count and named feature values. These are designed geographic features: counts, building measures, land-use area and proximity estimates.

4. Compare that location with the matrix:

   ```sh
   python location.py compare --lat 51.5117 --lng -0.124 --top 100 --json
   ```

   The scorer normalizes numeric dimensions, calculates Leo’s calibrated distance, excludes the nearby 15-ring neighbourhood and returns ranked cells and scores.

5. Connect a different geographic matrix with `--matrix PATH` or `RETAIL_MATRIX_PATH`. The same source functions operate across regions covered by compatible H3 resolution-10 data. Its coverage, features and source terms belong with that input.

## Product areas and source

| Area | Action and result | Source |
| --- | --- | --- |
| Location input | Supply coordinates or an H3 resolution-10 cell. | [location.py](../location.py): `coordinates`, CLI `--lat` / `--lng` / `--cell`. |
| Geographic embedding | Read the exact ordered numeric vector for that cell from your local matrix. | [location.py](../location.py): `embedding`; [ordered London schema](../data/london/schema.json). |
| Similarity search | Normalize dimensions, score other cells, exclude nearby locations and rank matches. | [diem_batch.py](../diem_batch.py): `search`. |
| Score equation | Convert normalized Euclidean distance into Leo’s calibrated 0–100 display score. | [_scoring.py](../_scoring.py): `compute_diem_parameters`, `compute_diem`. |
| Original example results | Inspect Covent Garden, Shoreditch and Soho immediately, with complete machine-readable output. | [location.py](../location.py), [retained results](../data/london/presets.json). |
| Matrix connector | Select your own local compatible Parquet or fetch the original London file with checksum verification. | [location.py](../location.py): `matrix_path`; [fetch tool](../tools/fetch_london.py). |
| Recompute examples | Calculate the three London references together in two passes. | [tools/precompute_london.py](../tools/precompute_london.py). |
| Optional local map | Inspect the original results on a browser map that you explicitly start on loopback. | [server.py](../server.py): `--local-map`; [index.html](../index.html). |
| Test fixture | Exercise the actual scorer with 90 generated records and five synthetic features. | [create_synthetic.py](../create_synthetic.py), [synthetic-example.parquet](../synthetic-example.parquet). |

## Scoring and data decisions

H3 provides a common spatial index. Min/max scaling makes differently sized feature dimensions comparable; zero-width features receive a safe width and missing values retain the historical midpoint treatment. The two-pass adapter reads batches of 512 rows. Nearby-cell exclusion encourages comparisons beyond the reference’s immediate area.

Leo’s analytic calibration and logistic display function are independently expressed here. They preserve the project’s historical approximation inspired by DIEM; the source docstring records the paper connection. This engineered feature vector is distinct from a learned neural embedding or sales model.

The retained global ETL source builds geographic features from Overture data and includes cloud-launch scripts. The reusable CLI in this repository reads local matrices. Executing those separate cloud scripts is a separate infrastructure action; they are source records rather than part of this setup.

## Continue from here

- [Data and full-query setup](london-data.md) provides the original download, schema, licence, provenance and reproduction steps.
- [Connections and services](services.md) describes local matrix configuration and optional network actions.
- [Third-party notices](../THIRD-PARTY-NOTICES.md) separate source, maps and geographic-data terms.
- [Geospatial Agent ETL](https://github.com/latintzar/geospatial-agent/tree/main/backend/etl/global) preserves the broader feature-building source. A completed global matrix remains unverified.

Useful extensions include an explicit feature-weighting interface and versioned build manifests for new regions. The original London matrix and functioning comparison are the verified achieved result.
