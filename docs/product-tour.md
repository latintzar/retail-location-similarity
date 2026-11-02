# Product tour

Retail Location Similarity is a geospatial comparison tool for retail operators and analysts. Choose a store whose performance you understand, then look for areas with similar map features. The engine compares geographic context; store sales and business performance remain your reference-selection inputs.

[Open demo](https://preview.atelierneyra.com/apps/retail-location-similarity/) · [Run locally](../README.md#run-locally)

## Compare a location

1. Choose **Covent Garden**. The app finds its H3 resolution-10 cell in the supplied feature matrix.
2. The scorer normalizes each numeric feature across that matrix and calculates a similarity score for the other cells. It excludes the reference cell’s 15-ring neighbourhood.
3. Read the matching-cell count and feature count. The map fits the reference and ranked matches; the leading five scores also appear in the results list.
4. Select a highlighted cell. Its popup carries the score and the app uses that cell as the next reference for another comparison.
5. Try **Shoreditch**, **Soho** or coordinates inside a supplied sample cell. This changes the reference while keeping the same feature schema and scoring method.

The public example uses 90 real H3 cell IDs with five generated feature values per record. The scores are actual calculations on those synthetic values. They demonstrate the workflow rather than observed London trading conditions.

## Product areas and source

| Area | Behavior | Source |
| --- | --- | --- |
| Reference and results UI | Three presets, coordinate form, highlighted polygons and leading scores. | [index.html](../index.html). |
| Local API | `/api/source` identifies the dataset; `/api/search` accepts bounded coordinates and returns matches. The server binds to loopback. | [server.py](../server.py): `Handler.do_GET`, `Handler.do_POST`. |
| Matrix search | Find the reference H3 cell, scan numeric dimensions, normalize, exclude nearby cells and rank the result. | [diem_batch.py](../diem_batch.py): `search`. |
| Similarity formula | Convert normalized Euclidean distance into Leo’s historical calibrated 0–100 display score. | [_scoring.py](../_scoring.py): `compute_diem_parameters`, `compute_diem`. |
| Example dataset | Reproduce the deterministic sample matrix. | [create_synthetic.py](../create_synthetic.py), [requirements.txt](../requirements.txt). |

## Scoring and data decisions

H3 supplies a consistent spatial index. Per-feature min/max scaling brings differently sized numeric dimensions onto a common range; zero-width features use a safe width, and missing values use the implementation’s midpoint treatment. The two-pass DuckDB scan reads bounded batches instead of materializing the whole matrix as one array.

Nearby-cell exclusion encourages comparisons beyond the immediate reference area. Similarity is calculated by Leo’s approximate distance calibration and logistic display function. This independently expressed implementation preserves the project’s historical equation; it is distinct from the published DIEM authors’ reference code. The source docstring records the paper connection.

The public server accepts one calculation at a time, caps response size through the selected match count and bounds worker duration. [server.py](../server.py) is the current local execution contract. Use a separately reviewed authentication and ingress arrangement when extending it into a network service.

## Continue from here

- [Local setup](../README.md#run-locally) runs the included matrix and scorer.
- [Module reference](#product-areas-and-source) identifies the small reusable implementation.
- [Third-party notices](../THIRD-PARTY-NOTICES.md) separate software and map-data terms.
- [Geospatial Agent tools and ETL](https://github.com/latintzar/geospatial-agent/tree/main/backend) retain the original broader feature-building work; its [data record](https://github.com/latintzar/geospatial-agent/blob/main/DATA-RIGHTS-AND-PROVENANCE.md) describes the separately held London matrix.

To continue, prepare an attributable matrix with `h3_index` and numeric feature columns, then adapt the explicit `MATRIX` input in `diem_batch.py` and its source metadata together. The historical 131,596-cell, 1,956-feature London result is separately recorded evidence. A completed global matrix remains unverified.
