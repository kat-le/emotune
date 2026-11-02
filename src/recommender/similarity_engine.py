# from functools import lru_cache

# import pandas as pd
# from sklearn.metrics.pairwise import euclidean_distances

# from src.recommender.feature_builder import (
#     load_song_data,
#     build_feature_matrix,
#     FEATURE_WEIGHT_PRESETS,
# )
# @lru_cache(maxsize=1)
# def _get_songs():
#     """Load and cache the song dataset."""
#     return load_song_data()


# @lru_cache(maxsize=len(FEATURE_WEIGHT_PRESETS))
# def _get_feature_data(preset="default"):
#     """Build and cache the feature matrix for a preset."""

#     songs = _get_songs()

#     if preset not in FEATURE_WEIGHT_PRESETS:
#         raise ValueError(f"Unknown preset: {preset}")

#     # Fit the scaler on the dataset and apply the selected weights.
#     matrix, columns, scaler = build_feature_matrix(
#         songs,
#         preset=preset,
#     )

#     return matrix, scaler


# def _apply_artist_diversity(recommendations, max_per_artist=2):
#     """Limit the number of recommendations per artist."""

#     selected = []
#     artist_counts = {}

#     for _, song in recommendations.iterrows():
#         artist = song["track_artist"]

#         if artist_counts.get(artist, 0) >= max_per_artist:
#             continue

#         selected.append(song)
#         artist_counts[artist] = artist_counts.get(artist, 0) + 1

#     return pd.DataFrame(selected)

# def _normalize_label(value):
#     """Normalize genre labels for consistent comparisons."""

#     if pd.isna(value):
#         return None

#     return str(value).strip().lower()


# def _calculate_genre_similarity(song_a, song_b):
#     """Calculate primary genre and subgenre matching scores."""

#     genre_a = _normalize_label(song_a.get("primary_genre"))
#     genre_b = _normalize_label(song_b.get("primary_genre"))

#     subgenre_a = _normalize_label(song_a.get("subgenre"))
#     subgenre_b = _normalize_label(song_b.get("subgenre"))

#     genre_score = (
#         1.0 if genre_a and genre_b and genre_a == genre_b else 0.0
#     )

#     subgenre_score = (
#         1.0
#         if subgenre_a and subgenre_b and subgenre_a == subgenre_b
#         else 0.0
#     )

#     return genre_score, subgenre_score


# # def get_similar_songs(
# #     track_id,
# #     top_k=10,
# #     preset="default",
# #     use_artist_diversity=True,
# # ):
# #     """Find songs that are musically similar to a selected track."""

# #     songs = _get_songs()

# #     matching_indices = songs.index[songs["track_id"] == track_id].tolist()

# #     if not matching_indices:
# #         raise ValueError(f"Song ID not found: {track_id}")

# #     song_index = matching_indices[0]

# #     matrix, scaler = _get_feature_data(preset)

# #     # Compare the selected song with every song using Euclidean distance.
# #     distances = euclidean_distances(
# #         matrix[song_index].reshape(1, -1),
# #         matrix,
# #     )[0]

# #     # Build a results table. Keep the existing `similarity` column name for
# #     # API compatibility; smaller values mean more similar songs.
# #     recommendations = songs.copy()
# #     recommendations["similarity"] = distances

# #     # Exclude the selected song.
# #     recommendations = recommendations.drop(
# #         index=song_index
# #     )

# #     # Sort from the smallest (closest) distance to the largest.
# #     recommendations = recommendations.sort_values(
# #         by="similarity",
# #         ascending=True,
# #     )

# #     # Limit recommendations from the same artist.
# #     if use_artist_diversity:
# #         recommendations = _apply_artist_diversity(
# #             recommendations,
# #             max_per_artist=2,
# #         )

# #     results = recommendations.head(top_k).copy()

# #     reference_song = songs.iloc[song_index]

# #     results["explanation"] = results.apply(
# #     lambda song: explain_similarity(
# #         reference_song,
# #         songs.loc[song.name],
# #         scaler=scaler,
# #         preset=preset,
# #     ),
# #     axis=1,
# # )

# #     return results[
# #         [
# #             "track_id",
# #             "track_name",
# #             "track_artist",
# #             "similarity",
# #             "explanation",
# #         ]
# #     ].reset_index(drop=True)

# def get_similar_songs(
#     track_id,
#     top_k=10,
#     preset="default",
#     use_artist_diversity=True,
# ):
#     """Find similar songs using audio features, genre, and subgenre."""

#     songs = _get_songs()

#     matching_indices = songs.index[
#         songs["track_id"] == track_id
#     ].tolist()

#     if not matching_indices:
#         raise ValueError(f"Song ID not found: {track_id}")

#     song_index = matching_indices[0]

#     matrix, scaler = _get_feature_data(preset)

#     reference_song = songs.iloc[song_index]

#     # Calculate Euclidean distances using audio features.
#     distances = euclidean_distances(
#         matrix[song_index].reshape(1, -1),
#         matrix,
#     )[0]

#     recommendations = songs.copy()

#     # Convert distance into a similarity score between 0 and 1.
#     # Higher scores indicate more similar songs.
#     recommendations["audio_similarity"] = 1 / (1 + distances)

#     # Calculate genre and subgenre matching scores.
#     genre_scores = []
#     subgenre_scores = []

#     for _, song in recommendations.iterrows():
#         genre_score, subgenre_score = _calculate_genre_similarity(
#             reference_song,
#             song,
#         )

#         genre_scores.append(genre_score)
#         subgenre_scores.append(subgenre_score)

#     recommendations["genre_similarity"] = genre_scores
#     recommendations["subgenre_similarity"] = subgenre_scores

#     # Combine all similarity scores.
#     recommendations["similarity"] = (
#         0.70 * recommendations["audio_similarity"]
#         + 0.20 * recommendations["subgenre_similarity"]
#         + 0.10 * recommendations["genre_similarity"]
#     )

#     # Exclude the selected song.
#     recommendations = recommendations.drop(index=song_index)

#     # Sort from highest similarity to lowest.
#     recommendations = recommendations.sort_values(
#         by="similarity",
#         ascending=False,
#     )

#     # Limit recommendations from the same artist.
#     if use_artist_diversity:
#         recommendations = _apply_artist_diversity(
#             recommendations,
#             max_per_artist=2,
#         )

#     results = recommendations.head(top_k).copy()

#     # Generate explanations for each recommendation.
#     results["explanation"] = results.apply(
#         lambda song: explain_similarity(
#             reference_song,
#             song,
#             scaler=scaler,
#             preset=preset,
#         ),
#         axis=1,
#     )

#     return results[
#         [
#             "track_id",
#             "track_name",
#             "track_artist",
#             "similarity",
#             "explanation",
#         ]
#     ].reset_index(drop=True)

# def get_similar_songs_by_name(
#     song_name,
#     top_k=10,
#     preset="default",
#     artist_name=None,
# ):
#     """Find similar songs using an exact or partial song title and optional artist."""

#     songs = _get_songs()
#     titles = songs["track_name"].fillna("")
#     artists = songs["track_artist"].fillna("")

#     # Prefer an exact title and exact artist match when the artist is specified.
#     if artist_name:
#         matches = songs[
#             (titles.str.lower() == song_name.lower().strip())
#             & (artists.str.lower() == artist_name.lower().strip())
#         ]
#         if matches.empty:
#             matches = songs[
#                 (titles.str.lower() == song_name.lower().strip())
#                 & artists.str.contains(artist_name.strip(), case=False, na=False)
#             ]
#     else:
#         matches = songs[titles.str.lower() == song_name.lower().strip()]

#     # A title-only request returns the first matching row if duplicate titles exist.
#     if matches.empty:
#         matches = songs[
#             titles.str.contains(song_name.strip(), case=False, na=False)
#         ]

#         if artist_name:
#             artist_matches = matches[
#                 artists.str.lower().str.contains(artist_name.lower().strip(), na=False)
#             ]
#             if not artist_matches.empty:
#                 matches = artist_matches

#     if matches.empty:
#         raise ValueError(f"Song not found: {song_name}")

#     track_id = matches.iloc[0]["track_id"]

#     return get_similar_songs(
#         track_id=track_id,
#         top_k=top_k,
#         preset=preset,
#     )

# def explain_similarity(
#     song_a,
#     song_b,
#     scaler,
#     preset="default",
#     top_features=3,
# ):
#     """Explain similarity using audio features and genre information."""

#     from src.recommender.feature_builder import (
#         AUDIO_FEATURES,
#         FEATURE_WEIGHT_PRESETS,
#     )

#     weights = FEATURE_WEIGHT_PRESETS[preset]

#     features_a = song_a[AUDIO_FEATURES].astype(float).to_numpy()
#     features_b = song_b[AUDIO_FEATURES].astype(float).to_numpy()

#     scaled_a = scaler.transform([features_a])[0]
#     scaled_b = scaler.transform([features_b])[0]

#     differences = {}

#     for i, feature in enumerate(AUDIO_FEATURES):
#         weight = weights.get(feature, 1.0)

#         differences[feature] = (
#             abs(scaled_a[i] - scaled_b[i]) * weight
#         )

#     feature_names = {
#         "danceability": "danceability",
#         "energy": "energy",
#         "loudness": "loudness",
#         "speechiness": "speechiness",
#         "acousticness": "acousticness",
#         "instrumentalness": "instrumentalness",
#         "liveness": "live-performance characteristics",
#         "valence": "emotional positivity",
#         "tempo": "tempo",
#     }

#     closest_features = sorted(
#         differences,
#         key=differences.get,
#     )[:top_features]

#     reasons = [
#         feature_names[feature]
#         for feature in closest_features
#     ]

#     # Add genre matching explanations.
#     genre_score, subgenre_score = _calculate_genre_similarity(
#         song_a,
#         song_b,
#     )

#     if genre_score:
#         reasons.append(
#             f"both songs are classified as {song_a['primary_genre']}"
#         )

#     if subgenre_score:
#         reasons.append(
#             f"both songs share the {song_a['subgenre']} subgenre"
#         )

#     return "Similar because of " + ", ".join(reasons)

# # def explain_similarity(
# #     song_a,
# #     song_b,
# #     scaler,
# #     preset="default",
# #     top_features=3,
# # ):
# #     """Explain similarity using scaled, weighted audio features."""

# #     from src.recommender.feature_builder import (
# #         AUDIO_FEATURES,
# #         FEATURE_WEIGHT_PRESETS,
# #     )

# #     weights = FEATURE_WEIGHT_PRESETS[preset]

# #     # Extract the raw audio features from both songs.
# #     features_a = song_a[AUDIO_FEATURES].astype(float).to_numpy()
# #     features_b = song_b[AUDIO_FEATURES].astype(float).to_numpy()

# #     # Apply the same scaler used by the recommendation engine.
# #     scaled_a = scaler.transform([features_a])[0]
# #     scaled_b = scaler.transform([features_b])[0]

# #     # Calculate the weighted difference for each feature.
# #     differences = {}

# #     for i, feature in enumerate(AUDIO_FEATURES):
# #         weight = weights.get(feature, 1.0)

# #         differences[feature] = (
# #             abs(scaled_a[i] - scaled_b[i]) * weight
# #         )

# #     # Select the features with the smallest weighted differences.
# #     closest_features = sorted(
# #         differences,
# #         key=differences.get,
# #     )[:top_features]

# #     feature_names = {
# #         "danceability": "danceability",
# #         "energy": "energy",
# #         "loudness": "loudness",
# #         "speechiness": "speechiness",
# #         "acousticness": "acousticness",
# #         "instrumentalness": "instrumentalness",
# #         "liveness": "live-performance characteristics",
# #         "valence": "emotional positivity",
# #         "tempo": "tempo",
# #     }

# #     return "Similar because of " + ", ".join(
# #         feature_names[feature]
# #         for feature in closest_features
# #     )


# if __name__ == "__main__":
#     import argparse

#     parser = argparse.ArgumentParser(
#         description="Find songs similar to a track using Euclidean distance."
#     )
#     parser.add_argument("track_id", nargs="?", default="2NO4CA2TFvhGeg7XMz8PmT")
#     parser.add_argument("--top-k", type=int, default=10)
#     parser.add_argument("--preset", default="default")
#     parser.add_argument("--no-artist-diversity", action="store_true")
#     args = parser.parse_args()

#     results = get_similar_songs(
#         track_id=args.track_id,
#         top_k=args.top_k,
#         preset=args.preset,
#         use_artist_diversity=not args.no_artist_diversity,
#     )

#     print(results.to_string(index=False))


import ast
from functools import lru_cache

import pandas as pd
from sklearn.metrics.pairwise import euclidean_distances

from src.recommender.feature_builder import (
    load_song_data,
    build_feature_matrix,
    FEATURE_WEIGHT_PRESETS,
)

# Map the labeled CSV's columns onto the names the engine uses.
COLUMN_MAP = {
    "id": "track_id",
    "name": "track_name",
    "artists": "track_artist",
    "genre": "primary_genre",
    "sub_genre": "subgenre",
}

# Blend weights for the final score (audio + subgenre + genre = 1.0).
AUDIO_WEIGHT = 0.8
SUBGENRE_WEIGHT = 0.1
GENRE_WEIGHT = 0.1

def _parse_artists(value):
    """Turn "['A', 'B']" into "A, B"; pass plain strings through."""

    if pd.isna(value):
        return value

    text = str(value).strip()

    if text.startswith("["):
        try:
            return ", ".join(str(a) for a in ast.literal_eval(text))
        except (ValueError, SyntaxError):
            pass

    return text


@lru_cache(maxsize=1)
def _get_songs():
    """Load and cache the song dataset with standardized column names."""

    songs = load_song_data().rename(columns=COLUMN_MAP)

    songs["track_artist"] = songs["track_artist"].map(_parse_artists)

    # Pre-normalize labels once so comparisons are cheap.
    songs["_genre_key"] = songs["primary_genre"].map(_normalize_label)
    songs["_subgenre_key"] = songs["subgenre"].map(_normalize_label)

    return songs


@lru_cache(maxsize=len(FEATURE_WEIGHT_PRESETS))
def _get_feature_data(preset="default"):
    """Build and cache the feature matrix for a preset."""

    songs = _get_songs()

    if preset not in FEATURE_WEIGHT_PRESETS:
        raise ValueError(f"Unknown preset: {preset}")

    matrix, columns, scaler = build_feature_matrix(songs, preset=preset)

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


def _normalize_label(value):
    """Normalize genre labels for consistent comparisons."""

    if pd.isna(value):
        return None

    return str(value).strip().lower()


def _calculate_genre_similarity(song_a, song_b):
    """Return (genre_match, subgenre_match) as 1.0 / 0.0 for two songs."""

    genre_a = _normalize_label(song_a.get("primary_genre"))
    genre_b = _normalize_label(song_b.get("primary_genre"))

    subgenre_a = _normalize_label(song_a.get("subgenre"))
    subgenre_b = _normalize_label(song_b.get("subgenre"))

    genre_score = 1.0 if genre_a and genre_a == genre_b else 0.0
    subgenre_score = 1.0 if subgenre_a and subgenre_a == subgenre_b else 0.0

    return genre_score, subgenre_score


def get_similar_songs(
    track_id,
    top_k=10,
    preset="default",
    use_artist_diversity=True,
):
    """Find similar songs using audio features, genre, and subgenre."""

    songs = _get_songs()

    matching_indices = songs.index[songs["track_id"] == track_id].tolist()

    if not matching_indices:
        raise ValueError(f"Song ID not found: {track_id}")

    song_index = matching_indices[0]

    matrix, scaler = _get_feature_data(preset)

    reference_song = songs.iloc[song_index]

    distances = euclidean_distances(
        matrix[song_index].reshape(1, -1),
        matrix,
    )[0]

    recommendations = songs.copy()

    # Higher = more similar (range 0-1).
    recommendations["audio_similarity"] = 1 / (1 + distances)

    # Vectorized genre / subgenre matches against the reference song.
    ref_genre = reference_song["_genre_key"]
    ref_subgenre = reference_song["_subgenre_key"]

    if ref_genre is None:
        recommendations["genre_similarity"] = 0.0
    else:
        recommendations["genre_similarity"] = (
            recommendations["_genre_key"] == ref_genre
        ).astype(float)

    if ref_subgenre is None:
        recommendations["subgenre_similarity"] = 0.0
    else:
        recommendations["subgenre_similarity"] = (
            recommendations["_subgenre_key"] == ref_subgenre
        ).astype(float)

    recommendations["similarity"] = (
        AUDIO_WEIGHT * recommendations["audio_similarity"]
        + SUBGENRE_WEIGHT * recommendations["subgenre_similarity"]
        + GENRE_WEIGHT * recommendations["genre_similarity"]
    )

    recommendations = recommendations.drop(index=song_index)

    recommendations = recommendations.sort_values(
        by="similarity",
        ascending=False,
    )

    if use_artist_diversity:
        recommendations = _apply_artist_diversity(
            recommendations,
            max_per_artist=2,
        )

    results = recommendations.head(top_k).copy()

    results["explanation"] = results.apply(
        lambda song: explain_similarity(
            reference_song,
            song,
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
            "primary_genre",
            "subgenre",
            "similarity",
            "explanation",
        ]
    ].reset_index(drop=True)


def get_similar_songs_by_name(
    song_name,
    top_k=10,
    preset="default",
    artist_name=None,
):
    """Find similar songs using an exact or partial song title and optional artist."""

    songs = _get_songs()
    titles = songs["track_name"].fillna("")
    artists = songs["track_artist"].fillna("")

    if artist_name:
        matches = songs[
            (titles.str.lower() == song_name.lower().strip())
            & (artists.str.lower() == artist_name.lower().strip())
        ]
        if matches.empty:
            matches = songs[
                (titles.str.lower() == song_name.lower().strip())
                & artists.str.contains(
                    artist_name.strip(), case=False, na=False, regex=False
                )
            ]
    else:
        matches = songs[titles.str.lower() == song_name.lower().strip()]

    if matches.empty:
        matches = songs[
            titles.str.contains(
                song_name.strip(), case=False, na=False, regex=False
            )
        ]

        if artist_name:
            artist_matches = matches[
                artists.loc[matches.index]
                .str.lower()
                .str.contains(
                    artist_name.lower().strip(), na=False, regex=False
                )
            ]
            if not artist_matches.empty:
                matches = artist_matches

    if matches.empty:
        raise ValueError(f"Song not found: {song_name}")

    track_id = matches.iloc[0]["track_id"]

    return get_similar_songs(track_id=track_id, top_k=top_k, preset=preset)


def explain_similarity(
    song_a,
    song_b,
    scaler,
    preset="default",
    top_features=3,
):
    """Explain similarity using audio features and genre information."""

    from src.recommender.feature_builder import AUDIO_FEATURES

    weights = FEATURE_WEIGHT_PRESETS[preset]

    features_a = song_a[AUDIO_FEATURES].astype(float).to_numpy()
    features_b = song_b[AUDIO_FEATURES].astype(float).to_numpy()

    scaled_a = scaler.transform([features_a])[0]
    scaled_b = scaler.transform([features_b])[0]

    differences = {
        feature: abs(scaled_a[i] - scaled_b[i]) * weights.get(feature, 1.0)
        for i, feature in enumerate(AUDIO_FEATURES)
    }

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

    closest_features = sorted(differences, key=differences.get)[:top_features]

    reasons = [feature_names[f] for f in closest_features]

    genre_score, subgenre_score = _calculate_genre_similarity(song_a, song_b)

    if genre_score:
        reasons.append(f"both songs are classified as {song_a['primary_genre']}")

    if subgenre_score:
        reasons.append(f"both songs share the {song_a['subgenre']} subgenre")

    return "Similar because of " + ", ".join(reasons)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Find songs similar to a track using audio features and genre."
    )
    parser.add_argument("track_id", nargs="?", default="5RNJtcXvXdTu8BqmFwXE8P")
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