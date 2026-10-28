from functools import lru_cache

import pandas as pd
from sklearn.metrics.pairwise import euclidean_distances

from src.recommender.feature_builder import (
    load_song_data,
    build_feature_matrix,
    FEATURE_WEIGHT_PRESETS,
)
@lru_cache(maxsize=1)
def _get_songs():
    """Load and cache the song dataset."""
    return load_song_data()


@lru_cache(maxsize=len(FEATURE_WEIGHT_PRESETS))
def _get_feature_data(preset="default"):
    """Build and cache the feature matrix for a preset."""

    songs = _get_songs()

    if preset not in FEATURE_WEIGHT_PRESETS:
        raise ValueError(f"Unknown preset: {preset}")

    # Fit the scaler on the dataset and apply the selected weights.
    matrix, columns, scaler = build_feature_matrix(
        songs,
        preset=preset,
    )

    return matrix, scaler


def _apply_artist_diversity(recommendations, max_per_artist=2):
    """Limit the number of recommendations per artist."""

    selected = []
    artist_counts = {}

    for _, song in recommendations.iterrows():
        artist = song["track_artist"]

        if artist_counts.get(artist, 0) >= max_per_artist:
            continue

        selected.append(song)
        artist_counts[artist] = artist_counts.get(artist, 0) + 1

    return pd.DataFrame(selected)


def get_similar_songs(
    track_id,
    top_k=10,
    preset="default",
    use_artist_diversity=True,
):
    """Find songs that are musically similar to a selected track."""

    songs = _get_songs()

    matching_indices = songs.index[songs["track_id"] == track_id].tolist()

    if not matching_indices:
        raise ValueError(f"Song ID not found: {track_id}")

    song_index = matching_indices[0]

    matrix, scaler = _get_feature_data(preset)

    # Compare the selected song with every song using Euclidean distance.
    distances = euclidean_distances(
        matrix[song_index].reshape(1, -1),
        matrix,
    )[0]

    # Build a results table. Keep the existing `similarity` column name for
    # API compatibility; smaller values mean more similar songs.
    recommendations = songs.copy()
    recommendations["similarity"] = distances

    # Exclude the selected song.
    recommendations = recommendations.drop(
        index=song_index
    )

    # Sort from the smallest (closest) distance to the largest.
    recommendations = recommendations.sort_values(
        by="similarity",
        ascending=True,
    )

    # Limit recommendations from the same artist.
    if use_artist_diversity:
        recommendations = _apply_artist_diversity(
            recommendations,
            max_per_artist=2,
        )

    results = recommendations.head(top_k).copy()

    reference_song = songs.iloc[song_index]

    results["explanation"] = results.apply(
    lambda song: explain_similarity(
        reference_song,
        songs.loc[song.name],
        scaler=scaler,
        preset=preset,
    ),
    axis=1,
)

    return results[
        [
            "track_id",
            "track_name",
            "track_artist",
            "similarity",
            "explanation",
        ]
    ].reset_index(drop=True)

  

def get_similar_songs_by_name(
    song_name,
    top_k=10,
    preset="default",
):
    """Find similar songs using a song title."""

    songs = _get_songs()

    matches = songs[
        songs["track_name"].str.lower() == song_name.lower()
    ]

    if matches.empty:
        matches = songs[
            songs["track_name"].str.contains(
                song_name,
                case=False,
                na=False,
            )
        ]

    if matches.empty:
        raise ValueError(f"Song not found: {song_name}")

    track_id = matches.iloc[0]["track_id"]

    return get_similar_songs(
        track_id=track_id,
        top_k=top_k,
        preset=preset,
    )


def explain_similarity(
    song_a,
    song_b,
    scaler,
    preset="default",
    top_features=3,
):
    """Explain similarity using scaled, weighted audio features."""

    from src.recommender.feature_builder import (
        AUDIO_FEATURES,
        FEATURE_WEIGHT_PRESETS,
    )

    weights = FEATURE_WEIGHT_PRESETS[preset]

    # Extract the raw audio features from both songs.
    features_a = song_a[AUDIO_FEATURES].astype(float).to_numpy()
    features_b = song_b[AUDIO_FEATURES].astype(float).to_numpy()

    # Apply the same scaler used by the recommendation engine.
    scaled_a = scaler.transform([features_a])[0]
    scaled_b = scaler.transform([features_b])[0]

    # Calculate the weighted difference for each feature.
    differences = {}

    for i, feature in enumerate(AUDIO_FEATURES):
        weight = weights.get(feature, 1.0)

        differences[feature] = (
            abs(scaled_a[i] - scaled_b[i]) * weight
        )

    # Select the features with the smallest weighted differences.
    closest_features = sorted(
        differences,
        key=differences.get,
    )[:top_features]

    feature_names = {
        "danceability": "danceability",
        "energy": "energy",
        "loudness": "loudness",
        "speechiness": "speechiness",
        "acousticness": "acousticness",
        "instrumentalness": "instrumentalness",
        "liveness": "live-performance characteristics",
        "valence": "emotional positivity",
        "tempo": "tempo",
    }

    return "Similar because of " + ", ".join(
        feature_names[feature]
        for feature in closest_features
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Find songs similar to a track using Euclidean distance."
    )
    parser.add_argument("track_id", nargs="?", default="6Yj8kVuVR3UPxx9r5eFEoV")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--preset", default="default")
    parser.add_argument("--no-artist-diversity", action="store_true")
    args = parser.parse_args()

    results = get_similar_songs(
        track_id=args.track_id,
        top_k=args.top_k,
        preset=args.preset,
        use_artist_diversity=not args.no_artist_diversity,
    )

    print(results.to_string(index=False))
