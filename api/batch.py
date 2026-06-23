import asyncio
import urllib.request
import json
import time
from pathlib import Path

# Tracking status
batch_status = {
    "chantiers_last_update": 0,
    "trafic_last_update": 0,
    "chantiers_interval": 3600,
    "trafic_interval": 300,
}

# The frontend public directory
PUBLIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "public" / "data"

def fetch_chantiers():
    url = "https://parisdata.opendatasoft.com/api/explore/v2.1/catalog/datasets/chantiers-a-paris/exports/geojson"
    try:
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.urlopen(url)
        data = req.read().decode('utf-8')
        
        out_path = PUBLIC_DIR / "chantiers_live.geojson"
        out_path.write_text(data, encoding="utf-8")
        batch_status["chantiers_last_update"] = int(time.time())
        print(f"[Batch] Chantiers mis à jour ({len(data)} bytes)")
    except Exception as e:
        print(f"[Batch] Erreur lors de la mise à jour des chantiers : {e}")

def fetch_trafic():
    # We fetch the latest 5000 records sorted by date to get the most recent state for each arc
    url = "https://parisdata.opendatasoft.com/api/explore/v2.1/catalog/datasets/comptages-routiers-permanents/exports/geojson?limit=5000&order_by=t_1h%20DESC"
    try:
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        req = urllib.request.urlopen(url)
        data = json.loads(req.read().decode('utf-8'))
        
        # Deduplicate by arc ID (iu_ac) to keep only the latest state
        seen_arcs = set()
        unique_features = []
        for feature in data.get("features", []):
            arc_id = feature.get("properties", {}).get("iu_ac")
            if arc_id and arc_id not in seen_arcs:
                seen_arcs.add(arc_id)
                unique_features.append(feature)
        
        data["features"] = unique_features
        
        out_path = PUBLIC_DIR / "trafic_live.geojson"
        out_path.write_text(json.dumps(data), encoding="utf-8")
        batch_status["trafic_last_update"] = int(time.time())
        print(f"[Batch] Trafic mis à jour ({len(unique_features)} arcs uniques)")
    except Exception as e:
        print(f"[Batch] Erreur lors de la mise à jour du trafic : {e}")

async def update_chantiers_batch():
    while True:
        await asyncio.to_thread(fetch_chantiers)
        await asyncio.sleep(3600)  # Refresh every hour

async def update_trafic_batch():
    while True:
        await asyncio.to_thread(fetch_trafic)
        await asyncio.sleep(300)  # Refresh every 5 minutes
