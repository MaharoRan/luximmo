import urllib.request
import json
import pandas as pd
from pathlib import Path

def main():
    print("Downloading chantiers data...")
    url = "https://parisdata.opendatasoft.com/api/explore/v2.1/catalog/datasets/chantiers-a-paris/exports/json"
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode('utf-8'))
    
    df = pd.DataFrame(data)
    
    # Save to Indicateur_1/raw/chantiers-a-paris.parquet
    out_dir = Path(__file__).resolve().parents[1] / "Indicateur_1" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "chantiers-a-paris.parquet"
    
    # Some columns might have dicts or lists, we convert them to string to save as parquet easily
    # WAIT! We need geo_point_2d as a dict! If we convert to string, we have to eval it later.
    # Better to extract lon/lat now, or just save as JSON?
    # Parquet can't natively save dicts unless schema is defined, let's just convert geo_point_2d to separate columns or save as string.
    # We will just extract lon and lat right here.
    if "geo_point_2d" in df.columns:
        df["longitude"] = df["geo_point_2d"].apply(lambda x: x.get("lon") if isinstance(x, dict) else None)
        df["latitude"] = df["geo_point_2d"].apply(lambda x: x.get("lat") if isinstance(x, dict) else None)
    
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
            df[col] = df[col].astype(str)
            
    df.to_parquet(out_path, index=False)
    print(f"Saved {len(df)} records to {out_path}")

if __name__ == "__main__":
    main()
