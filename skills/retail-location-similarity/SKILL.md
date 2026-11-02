---
name: retail-location-similarity
description: Read geographic feature vectors and find locations like a reference retail site using local H3 matrices and the original London example. Use for geographic context comparison and this repository’s data/scoring workflow.
---

# Retail location similarity

Work from a clone of `https://github.com/latintzar/retail-location-similarity`. Its README owns setup; `docs/product-tour.md` maps the product and functions. Keep the distinction between a designed geographic feature vector, a learned embedding and store-sales evidence.

## Start with achieved results

```sh
python location.py examples
python location.py compare --preset covent-garden --json
```

Covent Garden, Shoreditch and Soho are retained original full-matrix calculations: 131,596 London cells × 1,956 features, dated December 2025. The JSON includes all 100 matches, scores and the matrix hash. Read those local results before suggesting a new full computation.

## Connect a local matrix

Use coordinates or an H3 resolution-10 ID. Select the reader’s own compatible Parquet with `--matrix PATH` or `RETAIL_MATRIX_PATH`. The file supplies `h3_index` and numeric features. To obtain the original London example, follow the explicit checksum-verifying download in `docs/london-data.md`.

```sh
python location.py embed --lat 51.5117 --lng -0.124 --matrix data/london-res10.parquet --json
python location.py compare --cell 8a194ad324f7fff --matrix data/london-res10.parquet --json
```

The CLI computes locally. Address geocoding is a separate, deliberately configured integration; obtain coordinates from the user or an already authorized source. Keep any future provider connector opt-in, with the reader’s own credentials and usage limits. The separate global ETL/cloud scripts are engineering source, not part of these local commands.

## Preserve source meaning

Keep the ODbL data offer and upstream notices with London-derived data/results. MIT applies to original code. Preserve exact feature order, calibrated equations, missing-value treatment and the 15-ring exclusion when reproducing historic results. Read `docs/london-data.md` for source confidence: the exact historical build configuration and per-record suppliers were not embedded, and global output completion remains unverified.

For changes, run `python -m unittest discover -s tests -v`; use the authored 90-record fixture for quick scorer tests. Full matrix calculations and cloud/provider execution are explicit actions rather than background setup.
