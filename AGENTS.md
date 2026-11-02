# Retail Location Similarity

Read `README.md`, `docs/product-tour.md` and `docs/london-data.md` first. `skills/retail-location-similarity/SKILL.md` is the reusable agent entry.

- Default entry: `python location.py compare --preset covent-garden --json` reads an original retained result locally.
- Location input: coordinates or H3 resolution-10 cells; matrix input: `--matrix PATH` or `RETAIL_MATRIX_PATH`.
- Numerical setup: `pip install -r requirements.txt`; the original-data download is an explicit `python tools/fetch_london.py` action.
- Checks: `python -m unittest discover -s tests -v`.
- Keep source MIT and data ODbL/upstream terms separate. Preserve exact original data hashes, cache provenance and geographic coverage.
- Preserve the historical score equations and feature order. The shipped synthetic matrix is an explicitly named test fixture.
- Optional map execution requires `python server.py --local-map`. The CLI is the primary entry; hosted preview publication is outside this package’s current contract.

The separate global ETL/cloud-launch source is engineering evidence. The current setup reads local matrices and uses local computation; new provider or cloud execution has its own explicit account/credential/budget boundary.
