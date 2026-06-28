# LuxImmo

LuxImmo is a data pipeline and web application for exploring Paris real-estate indicators. The project follows a three-layer architecture:

- Raw: source datasets as they are collected from CSV, GeoJSON, and parquet inputs.
- Silver: cleaned, standardized, and enriched datasets ready for analytical use.
- Gold: aggregates and scores used by the API and frontend.

The repository also includes geographic reference data and live map layers used by the interface.

## Project structure

- `source/`: raw input files used by the pipeline.
- `Indicateur_*/raw/`: raw indicator inputs.
- `Indicateur_*/silver/`: cleaned parquet outputs.
- `Indicateur_*/gold/`: final parquet outputs consumed by the app.
- `geo/`: geographic reference data such as IRIS geometry.
- `api/`: FastAPI backend.
- `frontend/`: React + Vite frontend.
- `utils/`: scripts that run the pipeline and load data into databases.

## Data flow

1. Raw data is transformed by each indicator script in `Indicateur_0` to `Indicateur_4`.
2. Silver data is produced first, then loaded into PostGIS.
3. Gold data is produced next, then loaded into MongoDB.
4. Geographic reference data is also loaded into MongoDB for map and location use.

### Storage targets

- Silver layer -> PostGIS
  - Loader: `utils/load_to_postgis.py`
  - The loader scans `Indicateur_*/silver/` for parquet files.
  - Each file is written to a PostGIS table named from the indicator and file name.

- Gold layer -> MongoDB
  - Loader: `utils/load_golds_to_mongo.py`
  - The loader scans `Indicateur_*/gold/` for parquet files.
  - Each file is written to a MongoDB collection.

- Geo layer -> MongoDB
  - Loader: `utils/load_to_mongodb.py`
  - This script prepares geographic records and stores them in MongoDB.
  - It is used for reference/location data such as IRIS geometries.

## Requirements

- Python 3.10+ for the backend and pipeline scripts
- Node.js 18+ for the frontend
- PostgreSQL with the PostGIS extension
- MongoDB Atlas or a MongoDB instance

## Install dependencies

### Python

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r api/requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Run the pipeline

Run the scripts to download chantiers and trafics first, then the feeder, then the geo helper,  then silver scripts , and finally the gold scripts:

```bash
python utils/run_all_silvers.py
python utils/run_all_golds.py
```

If you want to load data separately:

```bash
python utils/load_to_postgis.py
python utils/load_golds_to_mongo.py
python utils/load_to_mongodb.py
```

## Launch the backend

From the project root:

```bash
cd api
python -m uvicorn main:app --reload
```

## Launch the frontend

```bash
cd frontend
npm run dev
```

Then open the local URL shown by Vite, usually `http://localhost:5173`.

## Notes

- The frontend reads map layers from `frontend/public/data/`.
- The API reads gold parquet files directly from the indicator folders.
- The batch jobs in `api/batch.py` refresh live GeoJSON files for construction and traffic layers.