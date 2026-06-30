import subprocess
import sys
import time
from pathlib import Path

try:
    import schedule
except ImportError:
    print("Please install schedule: pip install schedule")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]

def run_script(script_path: Path):
    if not script_path.exists():
        print(f"[{script_path.name}] File not found at {script_path}.")
        return False
        
    print(f"[{script_path.name}] Running...")
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[{script_path.name}] Success.")
        return True
    else:
        print(f"[{script_path.name}] Error:\n{result.stderr}")
        return False

def run_pipeline():
    print(f"\n--- Starting Full ETL Pipeline at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    scripts_to_run = [
        "utils/feeder.py",
        "utils/geo_helpers.py",
        "Indicateur_0/silver_ind0.py",
        "Indicateur_1/silver_ind1.py",
        "Indicateur_2/silver_ind2.py",
        "Indicateur_3/silver_ind3.py",
        "Indicateur_4/silver_ind4.py",
        "utils/load_to_postgis.py",
        "Indicateur_0/gold_ind0.py",
        "Indicateur_1/gold_ind1.py",
        "Indicateur_2/gold_ind2.py",
        "Indicateur_3/gold_ind3.py",
        "Indicateur_4/gold_ind4.py",
        "utils/load_golds_to_mongo.py",
        "utils/load_to_mongodb.py"
    ]
    
    for script in scripts_to_run:
        success = run_script(ROOT / script)
        if not success:
            print(f"Pipeline stopped due to error in {script}.")
            return
            
    print(f"--- Full ETL Pipeline completed successfully at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

def main():
    print("ETL Scheduler started. Running initial pipeline now...")
    run_pipeline()
    
    print("Initial run complete. Pipeline will now run every day at 03:00.")
    print("Leave this terminal open (or let Docker run it).")
    
    schedule.every().day.at("03:00").do(run_pipeline)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
