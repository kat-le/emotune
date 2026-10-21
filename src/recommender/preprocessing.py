from sklearn.preprocessing import StandardScaler

AUDIO_FEATURES = [
     "danceability",
    "energy",
    "valence",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "liveness",
    "loudness",
    "tempo",
]

def prepare_features(songs):
    missing_columns = [col for col in AUDIO_FEATURES if col not in songs.columns]

    if missing_columns:
        raise ValueError(f"The following required audio feature columns are missing from the dataset: {missing_columns}")

    features = songs[AUDIO_FEATURES]
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
    return scaled_features, scaler