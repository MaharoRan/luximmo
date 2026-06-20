from pathlib import Path
import pandas as pd
import sys

paths = sorted(Path('.').glob('Indicateur_*/gold/*.parquet'))
if not paths:
    print('No gold parquet found')
    sys.exit(0)

for p in paths:
    print('\n---', p, '---')
    try:
        df = pd.read_parquet(p)
        if df.empty:
            print('(empty)')
        else:
            print(df.head(10).to_string(index=False))
    except Exception as e:
        print('Error reading', p, ':', e)
