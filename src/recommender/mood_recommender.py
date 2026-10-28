
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import euclidean_distances, cosine_similarity

from src.recommender.feature_builder import (
    AUDIO_FEATURES,
    FEATURE_WEIGHT_PRESETS,
)

from src.recommender.similarity_engine import (
    _get_songs,
    _get_feature_data,
    _apply_artist_diversity,
)


# Target audio characteristics for each mood.
# Values are approximate starting points, not learned profiles.

MOOD_PROTOTYPES = {
    "happy": {
        "danceability": 0.85,
        "energy": 0.85,
        "loudness": -4,
        "speechiness": 0.05,
        "acousticness": 0.05,
        "instrumentalness": 0.0,
        "liveness": 0.2,
        "valence": 0.98,
        "tempo": 140,
    },

    "sad": {
        "danceability": 0.35,
        "energy": 0.30,
        "loudness": -10,
        "speechiness": 0.05,
        "acousticness": 0.65,
        "instrumentalness": 0.10,
        "liveness": 0.10,
        "valence": 0.15,
        "tempo": 75,
    },

    "energetic": {
        "danceability": 0.80,
        "energy": 0.95,
        "loudness": -3,
        "speechiness": 0.08,
        "acousticness": 0.05,
        "instrumentalness": 0.0,
        "liveness": 0.20,
        "valence": 0.75,
        "tempo": 145,
    },

    "calm": {
        "danceability": 0.35,
        "energy": 0.20,
        "loudness": -15,
        "speechiness": 0.04,
        "acousticness": 0.80,
        "instrumentalness": 0.20,
        "liveness": 0.10,
        "valence": 0.50,
        "tempo": 70,
    },

    "romantic": {
        "danceability": 0.50,
        "energy": 0.40,
        "loudness": -8,
        "speechiness": 0.04,
        "acousticness": 0.50,
        "instrumentalness": 0.05,
        "liveness": 0.10,
        "valence": 0.65,
        "tempo": 90,
    },

    "focus": {
        "danceability": 0.5,
        "energy": 0.2,
        "loudness": 0.5,
        "speechiness": 0.5,
        "acousticness": 2.0,
        "instrumentalness": 1.0,
        "liveness": 0.5,
        "valence": 0.8,
        "tempo": 1.5,
    },

    "nostalgic": {
        "danceability": 0.50,
        "energy": 0.45,
        "loudness": -8,
        "speechiness": 0.04,
        "acousticness": 0.35,
        "instrumentalness": 0.05,
        "liveness": 0.10,
        "valence": 0.50,
        "tempo": 100,
    },
}


def get_mood_recommendations(
    mood,
    top_k=10,
    preset="mood",
    use_artist_diversity=True,
):
    """Recommend songs based on a predefined mood profile."""

    mood = mood.lower().strip()

    if mood not in MOOD_PROTOTYPES:
        available = ", ".join(MOOD_PROTOTYPES.keys())
        raise ValueError(
            f"Unknown mood: {mood}. Available moods: {available}"
        )

    songs = _get_songs()

    # Get the song feature matrix and its fitted scaler.
    matrix, scaler = _get_feature_data(preset)

    # Convert the mood profile into the same feature order as the dataset.
    mood_values = np.array([
        MOOD_PROTOTYPES[mood][feature]
        for feature in AUDIO_FEATURES
    ]).reshape(1, -1)

    # Standardize the mood profile using the dataset's scaler.
    mood_scaled = scaler.transform(mood_values)

    # Apply the same feature weights used for the songs.
    weights = FEATURE_WEIGHT_PRESETS[preset]

    weight_array = np.array([
        weights.get(feature, 1.0)
        for feature in AUDIO_FEATURES
    ])

    mood_scaled = mood_scaled * weight_array

    distances = euclidean_distances(
            mood_scaled.reshape(1, -1),
            matrix
        ).flatten()

    # Apply additional penalties only to focus recommendations
    if mood == "focus":
        original_distances = distances.copy()
        energy_penalty = np.maximum(
                songs["energy"].to_numpy() - 0.60,
                0
            )
        
        acousticness_penalty = np.maximum(
                0.20 - songs["acousticness"].to_numpy(),
                0
            )

        distances = distances + (
            10.0 * energy_penalty
        ) + (
            10.0 * acousticness_penalty
        )
        
    
        top_indices = np.argsort(distances)[:10]

        print("\nFOCUS DISTANCE COMPARISON")

        for i in top_indices:
            penalty = (
                energy_penalty[i] * 3.0
                + acousticness_penalty[i] * 2.0
            )

            print(
                f"\n{songs.iloc[i]['track_name']}"
                f"\nOriginal distance: {original_distances[i]:.3f}"
                f"\nPenalty: {penalty:.3f}"
                f"\nAdjusted distance: {distances[i]:.3f}"
            )
    
    
    similarities = 1 / (1 + distances)



    recommendations = songs.copy()
    recommendations["similarity"] = similarities

    recommendations = recommendations.sort_values(
        by="similarity",
        ascending=False,
    )

    if use_artist_diversity:
        recommendations = _apply_artist_diversity(
            recommendations,
            max_per_artist=2,
        )

    return recommendations.head(top_k)[
        [
            "track_id",
            "track_name",
            "track_artist",
            "similarity",
        ] + AUDIO_FEATURES
    ].reset_index(drop=True)


if __name__ == "__main__":

    features = [
        "danceability",
        "energy",
        "valence",
        "acousticness",
        "instrumentalness",
        "tempo"
    ]

    moods = [
        "happy", "sad", "energetic",
        "calm", "romantic", "focus", "nostalgic"
    ]

    for mood in moods:
        recommendations = get_mood_recommendations(
            mood,
            top_k=10,
            preset="focus" if mood == "focus" else "mood"
        )

        print(f"\n{mood.upper()}")
        print(recommendations[features].mean().round(3))