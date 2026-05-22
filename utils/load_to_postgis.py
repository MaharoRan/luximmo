import os
from pathlib import Path
import urllib.parse
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine


def _read_env(env_path: str) -> dict:
    vals = {}
    if not os.path.exists(env_path):
        return vals
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()
    return vals


def build_db_uri_from_env(env: dict) -> str:
    user = env.get("POSTGRES_USER", "postgres")
    password = env.get("POSTGRES_PASSWORD", "")
    host = env.get("POSTGRES_HOST", "localhost")
    port = env.get("POSTGRES_PORT", "5432")
    db = env.get("POSTGRES_DB", "postgres")
    # quote password/user
    user_q = urllib.parse.quote_plus(user)
    password_q = urllib.parse.quote_plus(password)
    return f"postgresql+psycopg2://{user_q}:{password_q}@{host}:{port}/{db}"


def load_path_to_postgis(path: str, engine, table_name: str):
    try:
        # Try reading as GeoDataFrame first
        gdf = gpd.read_parquet(path)
        if isinstance(gdf, gpd.GeoDataFrame):
            gdf.to_postgis(table_name, engine, if_exists="replace", index=False)
            print(f"Wrote GeoDataFrame to PostGIS table: {table_name}")
            return
    except Exception:
        pass

    # fallback to pandas DataFrame
    try:
        df = pd.read_parquet(path)
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        print(f"Wrote DataFrame to SQL table: {table_name}")
    except Exception as e:
        print(f"Failed to load {path} -> {table_name}: {e}")


def load_silver_indicators(root_dir: str, indicators=(0, 1, 2, 3, 4)):
    # read .env from repo root
    env_path = os.path.join(root_dir, ".env")
    env = _read_env(env_path)
    db_uri = build_db_uri_from_env(env)

    engine = create_engine(db_uri)

    for i in indicators:
        ind_dir = Path(root_dir) / f"Indicateur_{i}"
        if not ind_dir.exists():
            continue
        # common silver locations
        candidates = [ind_dir / "silver", ind_dir / "silver" / "data"]
        for c in candidates:
            if not c.exists():
                continue
            for pq in c.glob("**/*.parquet"):
                table_name = f"ind{i}_" + pq.stem.replace("-", "_").replace(".", "_")
                load_path_to_postgis(str(pq), engine, table_name)


if __name__ == "__main__":
    # assume this utils folder is under project root 'luximmo'
    repo_root = Path(__file__).resolve().parents[0]
    # move up if utils/ is inside repo
    if repo_root.name == "utils":
        repo_root = repo_root.parent
    load_silver_indicators(str(repo_root), indicators=(0, 1, 2, 3, 4))
