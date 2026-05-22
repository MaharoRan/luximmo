import os
import requests
import pyarrow.parquet as pq
import pandas as pd
import geopandas as gpd
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_BASE = os.path.join(SCRIPT_DIR, "raw")
SILVER_BASE = os.path.join(SCRIPT_DIR, "silver")
os.makedirs(SILVER_BASE, exist_ok=True)

def clean_columns(df):
    cleaned = {}
    for c in df.columns:
        cleaned[c] = re.sub(r"[ ,;{}()\n\t=\-]", "_", c)
    return df.rename(columns=cleaned)

def object_to_string(val):
    if type(val) in (float, int) and pd.isna(val):
        return None
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.hex()
    return str(val)

def fetch_api(url, output_name):
    print(f"Fetching from {url}...")
    try:
        r = requests.get(url, params={"limit": 100})
        if r.status_code == 200:
            data = r.json()
            if "results" in data:
                df = pd.DataFrame(data["results"])
                df = clean_columns(df)
                for c in df.columns:
                    if df[c].dtype == 'object':
                        df[c] = df[c].apply(object_to_string)
                # gdf = gpd.GeoDataFrame(df)
                df.to_parquet(f"{SILVER_BASE}/{output_name}.parquet", engine="pyarrow", compression="snappy")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Fetch error: {e}")

def process_parquets():
    datasets = [f for f in os.listdir(RAW_BASE) if f.endswith(".parquet")]
    for ds in datasets:
        try:
            table = pq.read_table(f"{RAW_BASE}/{ds}")
            df = table.to_pandas()
            df = clean_columns(df)
            for c in df.columns:
                if df[c].dtype == 'object':
                    df[c] = df[c].apply(object_to_string)
            df.to_parquet(f"{SILVER_BASE}/{ds}", engine="pyarrow", compression="snappy")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)

if __name__ == "__main__":
    fetch_api("https://parisdata.opendatasoft.com/api/explore/v2.1/catalog/datasets/chantiers-a-paris/records", "chantiers")
    fetch_api("https://parisdata.opendatasoft.com/api/explore/v2.1/catalog/datasets/dans-ma-rue/records", "dans_ma_rue")
    process_parquets()






