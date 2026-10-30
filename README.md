# Retail Location Similarity

Retail Location Similarity is a map tool for comparing locations using H3 feature vectors and Leo’s calibrated distance score.

![Retail Location Similarity example](https://atelierneyra.com/assets/product-motion-v3/retail-location-similarity.jpg)

[Open demo](https://preview.atelierneyra.com/apps/retail-location-similarity/) · [Project website](https://atelierneyra.com/retail-location-similarity/) · [Documentation](https://docs.atelierneyra.com/retail-location-similarity/overview/) · [GitHub](https://github.com/latintzar/retail-location-similarity)

## What it does

Choose an example reference location or enter coordinates within the sample cells. The app normalizes numeric feature dimensions, computes similarity, excludes the nearby 15-ring H3 neighbourhood, and maps ranked matches. The bundled dataset contains 90 generated records and five synthetic features. Scores are actual calculations on those values; they do not describe real London locations.

## Run

Requires Python 3.10 or newer.

```sh
git clone https://github.com/latintzar/retail-location-similarity.git
cd retail-location-similarity
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Open http://127.0.0.1:18869. The map uses OpenStreetMap tiles. The synthetic scorer needs no account or provider credentials.

## Status and source

The independent scorer preserves Leo’s historical calibrated distance approximation inspired by DIEM; it is not the authors’ published reference implementation. A separate historical London matrix was privately verified at 131,596 H3 cells and 1,956 numeric features; it is not included. Completion of a global matrix has not been verified. The recovered agent’s [tools and ETL source](https://github.com/latintzar/geospatial-agent) contain the broader original work. Original code is MIT licensed; dependencies and map data retain their own terms.

## Agent instructions

Keep synthetic examples labelled and preserve the distinction between observed geographic data and generated features. Review data provenance and applicable third-party terms before substituting a real dataset. Run `python server.py` and exercise a preset after changes.
