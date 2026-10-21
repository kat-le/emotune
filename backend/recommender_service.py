
from typing import List, Dict, Optional
import logging

from src.recommender.mood_recommender import get_mood_recommendations
from src.recommender.similarity_engine import (
    _get_songs,
    get_similar_songs as get_similar_songs_engine,
    get_similar_songs_by_name as get_similar_songs_by_name_engine,
)

logger = logging.getLogger(__name__)
EMOTION_TO_MOOD = {
    "joy": "happy",
    "excitement": "energetic",
    "sadness": "sad",
    "anger": "energetic",
    "fear": "calm",
    "anxiety": "calm",
    "calmness": "calm",
    "concentration": "focus",
    "determination": "focus",
    "love": "romantic",
    "admiration": "romantic",
    "nostalgia": "nostalgic",
    "contentment": "calm",
}


def get_recommendations(
    top_emotion: str,
    all_emotions: List[Dict] = None,
    limit: int = 10,
    top_k: Optional[int] = None,
) -> List[Dict]:

    emotion = (top_emotion or "").lower().strip()

    # Accept moods directly, as well as Hume emotion names.
    supported_moods = [
        "happy", "sad", "energetic", "calm",
        "romantic", "focus", "nostalgic"
    ]

    if emotion in supported_moods:
        mood = emotion
    else:
        mood = _map_emotion_to_mood(emotion)

    if mood == UNKNOWN_MOOD:
        logger.info(f"Unknown emotion '{top_emotion}'.")
        return []

    try:
        count = top_k if top_k is not None else limit

        df = get_mood_recommendations(
            mood=mood,
            top_k=count,
        )

        records = df.to_dict(orient="records")
        records = _dedup_records(records)

        # Make values JSON serializable.
        for rec in records:
            for key, value in list(rec.items()):
                if isinstance(value, float) and (
                    value != value or value == float("inf")
                    or value == float("-inf")
                ):
                    rec[key] = None

        return records[:count]

    except Exception as e:
        logger.error(f"Recommender failed: {e}", exc_info=True)
        return []


def get_similar_songs_by_name(
    song_name: str,
    limit: int = 10,
    preset: Optional[str] = None,
    use_genre_boost: bool = True,
    use_artist_diversity: bool = True,
) -> List[Dict]:

    try:
        df = get_similar_songs_by_name_engine(
            song_name,
            top_k=limit,
            preset=preset or "default",
        )

        records = df.to_dict(orient="records")
        return _dedup_records(records)[:limit]

    except Exception as e:
        logger.error(f"Similar songs search failed: {e}", exc_info=True)
        return []

def get_song_by_track_id(track_id: str) -> Optional[Dict]:
    try:
        songs = _get_songs()
        matches = songs[songs["track_id"] == track_id]

        if matches.empty:
            logger.warning(f"No song found with track_id: {track_id}")
            return None

        song = matches.iloc[0].to_dict()

        for key, value in list(song.items()):
            if isinstance(value, float) and (
                value != value or value == float("inf")
                or value == float("-inf")
            ):
                song[key] = None

        return song

    except Exception as e:
        logger.error(f"Track ID lookup failed: {e}", exc_info=True)
        return None


def get_similar_songs_by_track_id(
    track_id: str,
    limit: int = 10,
    preset: Optional[str] = None,
    use_genre_boost: bool = True,
    use_artist_diversity: bool = True,
) -> List[Dict]:

    try:
        df = get_similar_songs_engine(
            track_id=track_id,
            top_k=limit,
            preset=preset or "default",
            use_artist_diversity=use_artist_diversity,
        )

        records = df.to_dict(orient="records")
        return _dedup_records(records)[:limit]

    except Exception as e:
        logger.error(f"Similar songs by track_id failed: {e}", exc_info=True)
        return []


UNKNOWN_MOOD = "unknown"


def _map_emotion_to_mood(emotion: str) -> str:
    """
    Map a Hume AI emotion name to a supported recommender mood.
    """
    key = (emotion or "").lower().strip()
    return EMOTION_TO_MOOD.get(key, UNKNOWN_MOOD)

def _dedup_records(records: List[Dict]) -> List[Dict]:
    """
    Remove duplicate recommendations based on track name and artist.
    Keeps the first occurrence.
    """
    seen = set()
    unique_records = []

    for rec in records:
        key = (rec.get("track_name"), rec.get("track_artist"))

        if key in seen:
            continue

        seen.add(key)
        unique_records.append(rec)

    return unique_records