
from __future__ import annotations

import ast
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


# Dataset configuration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "kpop_songs.csv"


# Audio features
AUDIO_FEATURES = [
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
]


# Metadata columns in the original CSV
REQUIRED_META = ["id", "name", "artists"]

EXCLUDED_SONGS = {
    ("y si fuera ella", "shinee"),
    ("aun en medio del dolor", "twice"),
    ("amor sin condición", "twice"),
}


# Feature weight presets
FEATURE_WEIGHT_PRESETS = {
    "default": {f: 1.0 for f in AUDIO_FEATURES},

    "mood": {
        "danceability": 0.8,
        "energy": 1.5,
        "loudness": 0.5,
        "speechiness": 0.3,
        "acousticness": 1.2,
        "instrumentalness": 1.0,
        "liveness": 0.3,
        "valence": 1.5,
        "tempo": 0.6,
    },

    "workout": {
        "danceability": 1.5,
        "energy": 2.0,
        "loudness": 1.0,
        "speechiness": 0.3,
        "acousticness": 0.3,
        "instrumentalness": 0.5,
        "liveness": 0.5,
        "valence": 0.8,
        "tempo": 1.5,
    },

    "chill": {
        "danceability": 0.5,
        "energy": 0.5,
        "loudness": 0.5,
        "speechiness": 0.3,
        "acousticness": 1.8,
        "instrumentalness": 1.5,
        "liveness": 0.3,
        "valence": 1.2,
        "tempo": 0.5,
    },

    "psychedelic": {
        "danceability": 1.0,
        "energy": 0.4,
        "loudness": 0.3,
        "speechiness": 0.2,
        "acousticness": 1.5,
        "instrumentalness": 2.0,
        "liveness": 0.3,
        "valence": 1.8,
        "tempo": 1.2,
    },

    "indie": {
        "danceability": 0.8,
        "energy": 0.7,
        "loudness": 0.5,
        "speechiness": 0.5,
        "acousticness": 1.5,
        "instrumentalness": 1.2,
        "liveness": 0.8,
        "valence": 1.3,
        "tempo": 1.0,
    },
    "focus": {
        "danceability": 0.8,
        "energy": 2.0,
        "loudness": 0.5,
        "speechiness": 0.5,
        "acousticness": 2.0,
        "instrumentalness": 1.5,
        "liveness": 0.5,
        "valence": 0.8,
        "tempo": 1.0,
    },
}

# Load song data
def load_song_data(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load and validate the K-pop song dataset."""

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path)

    # Convert original CSV column names to recommender names
    df = df.rename(columns={
        "id": "track_id",
        "name": "track_name",
        "artists": "track_artist",
    })

    # Format artist lists as readable strings
    def format_artist(value):
        if not isinstance(value, str):
            return value

        try:
            parsed = ast.literal_eval(value)

            if isinstance(parsed, list):
                return ", ".join(str(artist) for artist in parsed)

        except (ValueError, SyntaxError):
            pass

        return value

    df["track_artist"] = df["track_artist"].apply(format_artist)
    df = df.drop_duplicates(
        subset=["track_name", "track_artist"],
    )
    excluded = pd.Series(False, index=df.index)
    for title, artist in EXCLUDED_SONGS:
        excluded |= (
            df["track_name"].str.strip().str.casefold().eq(title)
            & df["track_artist"].str.strip().str.casefold().eq(artist)
        )
    df = df.loc[~excluded]

    # Validate required columns
    required_columns = ["track_id", "track_name", "track_artist"] + AUDIO_FEATURES

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return df


# Build feature matrix

def build_feature_matrix(
    df: pd.DataFrame,
    scaler: Optional[StandardScaler] = None,
    weights: Optional[dict] = None,
    preset: Optional[str] = None,
):
    """
    Standardize audio features and apply optional weights.

    Returns:
        X_scaled: Weighted feature matrix
        feature_cols: Audio feature names
        scaler: Fitted StandardScaler
    """

    # Select audio features
    X = df[AUDIO_FEATURES].astype(float)

    # Handle missing or infinite values using column medians
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median())

    X = X.to_numpy()

    # Fit scaler once, or reuse an existing scaler
    if scaler is None:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
    else:
        X_scaled = scaler.transform(X)

    # Select preset weights
    if preset is not None:
        if preset not in FEATURE_WEIGHT_PRESETS:
            raise ValueError(f"Unknown feature preset: {preset}")

        weights = FEATURE_WEIGHT_PRESETS[preset]

    # Apply feature weights
    if weights is not None:
        weight_array = np.array([
            weights.get(feature, 1.0)
            for feature in AUDIO_FEATURES
        ])

        X_scaled = X_scaled * weight_array

    return X_scaled, AUDIO_FEATURES, scaler
