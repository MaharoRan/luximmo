import urllib.request
import json
import pandas as pd
from pathlib import Path

def main():
    print("Downloading trafic data...")
    url = "https://parisdata.opendatasoft.com/api/explore/v2.1/catalog/datasets/comptages-routiers-permanents/exports/json?limit=5000&order_by=t_1h%20DESC"
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode('utf-8'))
    
    # Deduplicate by iu_ac
    seen_arcs = set()
    unique_records = []
    for record in data:
        arc_id = record.get("iu_ac")
        if arc_id and arc_id not in seen_arcs:
            seen_arcs.add(arc_id)
            unique_records.append(record)
            
    df = pd.DataFrame(unique_records)
    
    out_dir = Path(__file__).resolve().parents[1] / "Indicateur_1" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "trafic.parquet"
    
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
