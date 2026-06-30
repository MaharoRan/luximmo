# LuxImmo

LuxImmo is a data pipeline and web application for exploring Paris real-estate indicators. The project follows a three-layer architecture:

- Raw: source datasets as they are collected from CSV, GeoJSON, and parquet inputs.
- Silver: cleaned, standardized, and enriched datasets ready for analytical use.
- Gold: aggregates and scores used by the API and frontend.

The repository also includes geographic reference data and live map layers used by the interface.

## Architecture & Features

- **Frontend**: React + Vite application (port 5173).
- **Backend (API)**: FastAPI with Uvicorn (port 8000).
- **Databases**: PostgreSQL (with PostGIS) and MongoDB (Replica Set).
- **Security**: JWT Authentication (default user `admin` / `admin`).
- **Rate Limiting**: API endpoints are protected at 200 requests/minute per IP.
- **ETL Scheduler**: A unified pipeline (`utils/run_pipeline.py`) runs automatically every day at 03:00 AM.
- **100% Dockerized**: The entire project can be spun up using a single `docker-compose` command.

## Project structure

- `source/`: raw input files used by the pipeline.
- `Indicateur_*/raw/`: raw indicator inputs.
- `Indicateur_*/silver/`: cleaned parquet outputs.
- `Indicateur_*/gold/`: final parquet outputs consumed by the app.
- `geo/`: geographic reference data such as IRIS geometry.
- `api/`: FastAPI backend and authentication logic.
- `frontend/`: React + Vite frontend.
- `utils/`: unified scripts that run the pipeline (`run_pipeline.py`) and load data into databases.

## Data flow

1. Raw data is transformed by each indicator script in `Indicateur_0` to `Indicateur_4`.
2. Silver data is produced first, then loaded into PostGIS (`utils/load_to_postgis.py`).
3. Gold data is produced next, then loaded into MongoDB (`utils/load_golds_to_mongo.py`).
4. Geographic reference data is also loaded into MongoDB for map and location use.

## Configuration (.env)

Avant de lancer le projet (en Docker ou en local), vous devez créer un fichier `.env` à la racine du projet contenant vos identifiants et variables de configuration :

```env
# Configuration MongoDB
MONGO_HOST=localhost:27017
MONGO_IS_SRV=false
MONGO_REPLICA_SET=rs0
MONGO_USER=
MONGO_PASSWORD=

# Configuration PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_USER=
POSTGRES_PASSWORD=

# Configuration Authentification API
API_USER=
API_PASSWORD=
JWT_SECRET_KEY=
```

> **Note :** Si vous utilisez Docker, les conteneurs utiliseront automatiquement ces variables (avec des redirections réseau gérées en interne par `docker-compose`).

## Quick Start (Docker)

The project is fully containerized. You do **not** need to install Python, Node.js, Postgres, or MongoDB locally.

1. Clone the repository and navigate to the root directory.
2. Assurez-vous d'avoir créé le fichier `.env` comme indiqué ci-dessus.
3. Run the following command:

```bash
docker-compose up -d --build
```

This single command will:
- Start the **MongoDB** replica set.
- Start the **PostgreSQL** database with PostGIS.
- Start the **API** on `http://localhost:8000`.
- Start the **Frontend** on `http://localhost:5173`.
- Start the **ETL Worker**, which will immediately run the entire data pipeline once, and then schedule itself to run every day at 03:00 AM.

### Accessing the services
- **Web App**: http://localhost:5173
- **API Swagger**: http://localhost:8000/docs
- **ETL Logs**: Run `docker-compose logs -f etl` to watch the data pipeline running.

## Local Development (Without Docker)

If you wish to run components locally for development purposes, you must manually install the dependencies:

### Python Dependencies
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r api/requirements.txt
```

### Frontend Dependencies
```bash
cd frontend
npm install
npm run dev
```

### Running the Pipeline Manually
```bash
python utils/run_pipeline.py
```

## Notes

- The frontend reads map layers from `frontend/public/data/`.
- The API reads gold parquet files directly from the indicator folders.
- The batch jobs in `api/batch.py` refresh live GeoJSON files for construction and traffic layers in the background.