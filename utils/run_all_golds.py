import subprocess
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    
    scripts = [
        "Indicateur_0/gold_ind0.py",
        "Indicateur_1/gold_ind1.py",
        "Indicateur_2/gold_ind2.py",
        "Indicateur_3/gold_ind3.py",
        "Indicateur_4/gold_ind4.py"
    ]
    
    print("Starting execution of all gold scripts...\n")
    
    for script in scripts:
        script_path = root / script
        if script_path.exists():
            print(f"[{script}] Running...")
            result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[{script}] Success.")
                if result.stdout:
                    print(result.stdout)
            else:
                print(f"[{script}] Error:\n{result.stderr}")
        else:
            print(f"[{script}] File not found.")
            
    print("\nAll gold scripts executed.")

    # Load to MongoDB
    loader_script = root / "utils" / "load_golds_to_mongo.py"
    if loader_script.exists():
        print("\nStarting to load gold files to MongoDB...")
        result = subprocess.run([sys.executable, str(loader_script)], capture_output=True, text=True)
        if result.returncode == 0:
            print("Successfully loaded all gold files to MongoDB.")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"Error loading to MongoDB:\n{result.stderr}")
    else:
        print("\nLoader script utils/load_golds_to_mongo.py not found.")

if __name__ == "__main__":
    main()
