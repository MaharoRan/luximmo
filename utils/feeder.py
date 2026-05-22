import os
import shutil

# Mapping of indicators to their respective files
INDICATOR_FILES = {
    "Indicateur_0": [
        "ValeursFoncieres-2021.csv",
        "ValeursFoncieres-2022.csv",
        "ValeursFoncieres-2023.csv",
        "ValeursFoncieres-2024.csv",
        "ValeursFoncieres-2025.csv"
    ],
    "Indicateur_1": [
        "ilots-de-fraicheur-espaces-verts-frais.parquet",
        "les-arbres.parquet",
        "ilots-de-fraicheur-equipements-activites.parquet",
        "eclairage-public.parquet",
        "sanisettesparis.parquet",
        "zones-touristiques-internationales.parquet"
    ],
    "Indicateur_2": [
        "ilots-de-fraicheur-espaces-verts-frais.parquet",
        "les-arbres.parquet",
        "que-faire-a-paris.parquet",
        "liste_des_associations_parisiennes.parquet",
        "lieux-de-tournage-a-paris.parquet",
        "zones-touristiques-internationales.parquet",
        "plan de voirie.parquet"
    ],
    "Indicateur_3": [
        "etablissements-scolaires-ecoles-elementaires.parquet",
        "secteurs-scolaires-colleges.parquet",
        "secteurs-scolaires-maternelles.parquet",
        "postes-publics-des-bibliotheques.parquet",
        "hopitaux.parquet",
        "carte-des-points-daccueil-police-a-paris.csv",
        "les_bureaux_de_poste_et_agences_postales_en_idf.parquet",
        "pharmacies.parquet",
        "plan de voirie.parquet"
    ],
    "Indicateur_4": [
        "velib-emplacement-des-stations.parquet",
        "amenagements-cyclables.parquet",
        "emplacement-des-gares-idf.csv",
        "plan de voirie.parquet"
    ]
}

def distribute_files(source_dir, base_dir):
    for indicator, files in INDICATOR_FILES.items():
        target_dir = os.path.join(base_dir, indicator, "raw")
        
        # Create target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        
        for file_name in files:
            source_file = os.path.join(source_dir, file_name)
            target_file = os.path.join(target_dir, file_name)
            
            # Check if source file exists
            if not os.path.exists(source_file):
                # print(f"Warning: Source file not found - {source_file}")
                continue
                
            # Copy if it doesn't exist in target
            if not os.path.exists(target_file):
                print(f"Copying {file_name} to {target_dir}")
                shutil.copy2(source_file, target_file)
            else:
                print(f"File already exists - {target_file}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    source_directory = os.path.join(project_root, "source")
    
    distribute_files(source_directory, project_root)
