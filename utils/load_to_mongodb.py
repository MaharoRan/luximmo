from pathlib import Path
import os
from urllib.parse import quote_plus

import pandas as pd
from pymongo import MongoClient
from shapely.geometry import mapping
from shapely import wkb

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"


def _load_env_file(env_path):
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


_load_env_file(ENV_PATH)


def _get_mongo_credentials():
    user = os.getenv("MONGO_USER")
    password = os.getenv("MONGO_PASSWORD")

    if user is None or password is None:
        raise ValueError("MONGO_USER or MONGO_PASSWORD not set")
    return user, password


def _build_mongo_uri(host, user, password, is_srv=True, replica_set=None):
    query_parts = ["retryWrites=true", "w=majority"]
    
    if "localhost" in host or "127.0.0.1" in host:
        query_parts.append("directConnection=true")
        # Try to find which local port is the primary to avoid NotWritablePrimary error
        try:
            from pymongo import MongoClient
            for port in [27017, 27018]:
                temp_client = MongoClient(f"mongodb://localhost:{port}/?directConnection=true", serverSelectionTimeoutMS=1000)
                if temp_client.admin.command("ismaster").get("ismaster"):
                    host = f"localhost:{port}"
                    break
        except Exception:
            pass
    elif replica_set:
        query_parts.append(f"replicaSet={replica_set}")

    if user and password:
        if is_srv:
            return f"mongodb+srv://{quote_plus(user)}:{quote_plus(password)}@{host}/?{'&'.join(query_parts)}"

        return f"mongodb://{quote_plus(user)}:{quote_plus(password)}@{host}/?{'&'.join(query_parts)}"

    if is_srv:
        return f"mongodb+srv://{host}/?{'&'.join(query_parts)}"

    return f"mongodb://{host}/?{'&'.join(query_parts)}"


def _resolve_input_path(input_path):
    path = Path(input_path)

    if path.is_absolute():
        return path

    candidate = BASE_DIR / path
    if candidate.exists():
        return candidate

    candidate = BASE_DIR / "data" / path
    if candidate.exists():
        return candidate

    return BASE_DIR / "data" / path.name


def _to_geojson(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, (bytes, bytearray, memoryview)):
        return mapping(wkb.loads(bytes(value)))

    return value


def _prepare_records(df):
    records = df.to_dict("records")

    for record in records:
        if "geo_point_2d" in record:
            record["location"] = _to_geojson(record["geo_point_2d"])

        if "geo_shape" in record:
            record["geometry"] = _to_geojson(record["geo_shape"])

        record.pop("geo_point_2d", None)
        record.pop("geo_shape", None)

    return records

def load_to_mongodb(input_path, mongo_uri, database, collection):
    resolved_path = _resolve_input_path(input_path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"Parquet introuvable: {resolved_path}")

    # Lecture robuste sans dépendre des métadonnées GeoParquet
    df = pd.read_parquet(resolved_path)

    # Préparer des documents MongoDB sérialisables
    records = _prepare_records(df)

    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[database]
    col = db[collection]

    # Insert documents
    if records:
        col.insert_many(records)

    print(f"Data loaded into MongoDB collection: {collection}")

if __name__ == "__main__":
    mongo_user, mongo_password = _get_mongo_credentials()

    mongo_host = os.getenv("MONGO_HOST") or "cluster0.3bidwmj.mongodb.net"
    mongo_is_srv = os.getenv("MONGO_IS_SRV", "true").lower() == "true"
    mongo_replica_set = os.getenv("MONGO_REPLICA_SET", "rs0")

    load_to_mongodb(
        "../geo/iris.parquet",
        _build_mongo_uri(
            mongo_host,
            mongo_user,
            mongo_password,
            is_srv=mongo_is_srv,
            replica_set=mongo_replica_set if not mongo_is_srv else None,
        ),
        "dataarchi",
        "location"
    )
