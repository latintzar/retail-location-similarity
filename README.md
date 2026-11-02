# Retail Location Similarity

Find retail locations similar to your best-performing stores

Retail Location Similarity is a geospatial tool for comparing potential locations with a known reference store. It represents each area as an H3 feature vector, calculates Leo’s calibrated distance score and shows the closest matches on a map.

[Open demo](https://preview.atelierneyra.com/apps/retail-location-similarity/) · [Project website](https://atelierneyra.com/retail-location-similarity/) · [Product tour](docs/product-tour.md) · [Documentation](https://docs.atelierneyra.com/retail-location-similarity/overview/)

![Retail Location Similarity](https://atelierneyra.com/assets/product-motion-v4/retail-location-similarity.jpg)

## Product areas

| Area | What you can do |
| --- | --- |
| Reference location | Choose Covent Garden, Shoreditch or Soho, or enter coordinates within the supplied sample cells. |
| Feature comparison | Normalize numeric dimensions and calculate location similarity. |
| Nearby exclusion | Compare other areas after excluding the reference cell’s immediate 15-ring H3 neighbourhood. |
| Ranked map | Inspect highlighted matches, similarity scores and the leading results; select a cell as the next reference. |
| Reusable scorer | Run the Python/DuckDB calculation with a feature matrix you can use and attribute. |

## Explore the example

Choose **Covent Garden**, wait for the calculated matches, then select a highlighted cell to compare from that location. The [product tour](docs/product-tour.md) follows the calculation and links its controls, scorer and data generator.

The bundled matrix contains 90 generated records across five synthetic features. Coordinates identify real H3 cells; the feature values illustrate the method. You choose a reference store using your own performance records; this engine compares its geographic context.

## Run locally

Requires Python 3.10 or newer.

```sh
git clone https://github.com/latintzar/retail-location-similarity.git
cd retail-location-similarity
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Open **http://127.0.0.1:18869**. The calculation runs locally with the included generated data. The map uses OpenStreetMap tiles.

## Source and data

The independently expressed scorer preserves Leo’s historical calibrated distance approximation inspired by DIEM. [Product decisions and source map](docs/product-tour.md#scoring-and-data-decisions) explain its distinction from the authors’ reference implementation.

A separate historical London matrix was privately verified at 131,596 H3 cells and 1,956 numeric features; it remains outside this package. Global matrix completion remains unverified. The recovered [Geospatial Agent tools and ETL source](https://github.com/latintzar/geospatial-agent) contain the broader original work.

Original code is [MIT licensed](LICENSE). Dependencies, map tiles and geographic data retain their [own terms](THIRD-PARTY-NOTICES.md). Keep generated inputs labelled and review the provenance of a replacement matrix.

[made by atelier neyra](https://atelierneyra.com)
