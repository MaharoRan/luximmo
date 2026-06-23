import os
import sys
from pathlib import Path
import pandas as pd
from pymongo import MongoClient
from urllib.parse import quote_plus

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from utils.load_to_mongodb import _get_mongo_credentials, _build_mongo_uri, _prepare_records

def load_parquet_to_mongodb(file_path, database, collection, mongo_uri):
    """Loads a single parquet file into a MongoDB collection."""
    print(f"Loading {file_path.name} into MongoDB collection {collection}...")
    
    try:
        df = pd.read_parquet(file_path)
        records = _prepare_records(df)
        
        if not records:
            print(f"No records found in {file_path.name}. Skipping.")
            return

        client = MongoClient(mongo_uri)
        db = client[database]
        col = db[collection]
        
        # Clear existing data in the collection to avoid duplicates if re-running
        col.delete_many({})
        
        col.insert_many(records)
        print(f"Successfully loaded {len(records)} documents into {collection}.")
        client.close()
    except Exception as e:
        print(f"Error loading {file_path.name} into MongoDB: {e}")

def load_all_golds(database_name="dataarchi"):
    """Finds all gold parquet files and loads them into MongoDB."""
    mongo_user, mongo_password = _get_mongo_credentials()
    mongo_host = "cluster0.3bidwmj.mongodb.net" # From load_to_mongodb.py template
    
    mongo_uri = _build_mongo_uri(mongo_host, mongo_user, mongo_password)
    
    gold_files = list(REPO_ROOT.glob("Indicateur_*/gold/*.parquet"))
    
    if not gold_files:
        print("No gold parquet files found. Make sure to run the gold scripts first.")
        return

    for gold_file in gold_files:
        # Collection name: indicator name + file name (without extension)
        indicator_name = gold_file.parents[1].name
        file_name = gold_file.stem
        collection_name = f"{indicator_name}_{file_name}".lower()
        
        load_parquet_to_mongodb(gold_file, database_name, collection_name, mongo_uri)

if __name__ == "__main__":
    load_all_golds()
