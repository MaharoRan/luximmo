import subprocess
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    
    scripts = [
        "Indicateur_0/silver_ind0.py",
        "Indicateur_1/silver_ind1.py",
        "Indicateur_2/silver_ind2.py",
        "Indicateur_3/silver_ind3.py",
        "Indicateur_4/silver_ind4.py",
        "utils/load_to_postgis.py"
    ]
    
    print("Starting execution of all silver scripts...\n")
    
    for script in scripts:
        script_path = root / script
        if script_path.exists():
            print(f"[{script}] Running...")
            result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[{script}] Success.")
            else:
                print(f"[{script}] Error:\n{result.stderr}")
        else:
            print(f"[{script}] File not found.")
            
    print("\nAll silver scripts executed.")

if __name__ == "__main__":
    main()
