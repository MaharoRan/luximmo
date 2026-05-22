import os
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

def process_parquets():
    datasets = [f for f in os.listdir(RAW_BASE) if f.endswith(".parquet") or f.endswith(".csv")]
    for ds in datasets:
        try:
            if ds.endswith(".parquet"):
                table = pq.read_table(f"{RAW_BASE}/{ds}")
                df = table.to_pandas()
            else:
                df = pd.read_csv(f"{RAW_BASE}/{ds}", sep=";", on_bad_lines="skip")
            df = clean_columns(df)
            gdf = gpd.GeoDataFrame(df)
            gdf.to_parquet(f"{SILVER_BASE}/{ds.replace('.csv', '.parquet')}", engine="pyarrow", compression="snappy")
        except Exception as e:
            pass

if __name__ == "__main__":
    process_parquets()


