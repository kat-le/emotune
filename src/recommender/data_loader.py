from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "kpop_songs.csv"

def load_songs():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Data file not found at {DATA_PATH}. Please ensure the file exists.")
    
    return pd.read_csv(DATA_PATH)


if __name__ == "__main__":
    songs = load_songs()

    print("Dataset loaded successfully!")
    print(f"Number of songs: {len(songs)}")
    print(f"Number of columns: {len(songs.columns)}")

    print("\nColumn names:")
    print(songs.columns.tolist())

    print("\nFirst 5 songs:")
    print(songs.head())

    print("\nMissing values:")
    print(songs.isnull().sum())