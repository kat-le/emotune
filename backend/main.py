import os
import tempfile
from dotenv import load_dotenv
import requests
from pydantic import BaseModel, Field, model_validator

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from backend.emotion_service import EmotionDetectionService
from backend.recommender_service import get_recommendations, get_similar_songs_by_name, get_song_by_track_id, get_similar_songs_by_track_id

app = FastAPI(
    title="Emotune Recommender API",
    description="Music recommendation system based on emotional analysis of text and audio",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize emotion detection service
emotion_service = EmotionDetectionService()


class TextRecommendationRequest(BaseModel):
    """
    Request model for generating song recommendations
    based on a user's mood or emotional context.
    """

    text: Optional[str] = None
    mood: Optional[str] = None
    current_mood: Optional[str] = None
    desired_mood: Optional[str] = None
    intensity: int = Field(default=3, ge=1, le=5)
    top_n: int = Field(default=5, ge=1, le=20)

    @model_validator(mode="after")
    def validate_request(self):
        # Either a direct mood or analyzed text with
        # a desired mood must be provided.

        if self.mood:
            return self

        if self.text and self.text.strip() and self.desired_mood:
            return self

        raise ValueError(
            "Provide either a mood or text with a desired mood."
        )


class TextRequest(BaseModel):
    text: Optional[str] = None
    mood: Optional[str] = None
    top_n: int = 10


class SimilarSongsRequest(BaseModel):
    song_name: str
    top_n: int = 10
    preset: Optional[str] = None  # "mood", "workout", "chill", "psychedelic"
    use_genre_boost: bool = True
    use_artist_diversity: bool = True


class SpotifyTrackRequest(BaseModel):
    track_id: str
    top_n: int = 10
    preset: Optional[str] = None  # "mood", "workout", "chill", "psychedelic"
    use_genre_boost: bool = True
    use_artist_diversity: bool = True


class RecommendationResponse(BaseModel):
    emotions: List[dict]
    top_emotion: str
    top_score: float
    recommendations: List[dict]


class SimilarSongsResponse(BaseModel):
    query_song: str
    found: bool
    recommendations: List[dict]


class SpotifyTrackResponse(BaseModel):
    track_id: str
    found: bool
    track_name: Optional[str] = None
    track_artist: Optional[str] = None
    recommendations: List[dict]


@app.get("/")
async def root():
    return {
        "message": "Emotune Recommender API",
        "endpoints": {
            "recommend_from_audio": "POST /api/recommend/audio",
            "recommend_from_text": "POST /api/recommend/text"
        }
    }


@app.post("/api/recommend/audio", response_model=RecommendationResponse)
async def recommend_from_audio(file: UploadFile = File(...)):
    """
    Upload an audio file to detect emotions using Hume AI prosody analysis,
    then get personalized song recommendations based on detected emotions.
    
    Flow:
    1. User uploads audio file
    2. Hume AI analyzes emotions/prosody from the audio
    3. Emotions are passed to the recommender system
    4. Returns detected emotions and recommended songs
    """
    # Validate file type: accept if content_type indicates audio/video, or infer from filename extension
    allowed_exts = {'.mp3', '.m4a', '.wav', '.flac', '.aac', '.ogg', '.opus', '.wma', '.m4b', '.mp4'}
    def _looks_like_audio(upload_file: UploadFile) -> bool:
        if upload_file.content_type and upload_file.content_type.startswith(('audio/', 'video/')):
            return True
        # Fallback: infer from filename extension
        if upload_file.filename:
            _, ext = os.path.splitext(upload_file.filename.lower())
            if ext in allowed_exts:
                return True
        return False

    if not _looks_like_audio(file):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an audio or video file. If using the OpenAPI docs, set the file's MIME to an audio type."
        )
    
    # Save uploaded file temporarily
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Step 1: Analyze emotions using Hume AI
        emotions = await emotion_service.analyze_audio(tmp_path)
        
        top_emotion = emotions[0]["name"]
        top_score = emotions[0]["score"]
        
        recommendations = get_recommendations(top_emotion, emotions)
        
        return RecommendationResponse(
            emotions=emotions,
            top_emotion=top_emotion,
            top_score=top_score,
            recommendations=recommendations
        )
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/recommend/text", response_model=RecommendationResponse)
async def recommend_from_text(request: TextRecommendationRequest):
    if request.mood:
        target_mood = request.mood
    else:
        target_mood = request.desired_mood

    # Validate that the mood is supported
    supported_moods = [
        "happy",
        "sad",
        "energetic",
        "calm",
        "romantic",
        "focus",
        "nostalgic"
    ]


    if target_mood not in supported_moods:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported mood: {target_mood}"
        )

    emotions = [
        {"name": target_mood, "score": 1.0}
    ]

    recommendations = get_recommendations(
        top_emotion=target_mood,
        all_emotions=emotions,
        top_k=request.top_n
    )

    return RecommendationResponse(
        emotions=emotions,
        top_emotion=target_mood,
        top_score=1.0,
        recommendations=recommendations
    )
    
@app.post("/api/recommend/similar", response_model=SimilarSongsResponse)
async def recommend_similar_songs(request: SimilarSongsRequest):
    """
    Find songs similar to a given song by name.
    Uses audio feature similarity (danceability, energy, valence, tempo, etc.)
    
    Flow:
    1. User provides a song name
    2. System searches for the song in the database
    3. If found, returns songs with similar audio features
    
    Optional parameters:
    - preset: Feature weight preset ("mood", "workout", "chill", "psychedelic")
    - use_genre_boost: Boost same-genre tracks (default: True)
    - use_artist_diversity: Limit songs per artist (default: True)
    """
    recommendations = get_similar_songs_by_name(
        request.song_name,
        request.top_n,
        preset=request.preset,
        use_genre_boost=request.use_genre_boost,
        use_artist_diversity=request.use_artist_diversity,
    )
    
    return SimilarSongsResponse(
        query_song=request.song_name,
        found=len(recommendations) > 0,
        recommendations=recommendations
    )


@app.post("/api/recommend/spotify", response_model=SpotifyTrackResponse)
async def recommend_from_spotify_track(request: SpotifyTrackRequest):
    """
    Look up a song by Spotify track ID and find similar songs.
    
    Flow:
    1. User provides a Spotify track ID (from a Spotify URL)
    2. System looks up the song in the database
    3. If found, returns song info and similar songs based on audio features
    
    Optional parameters:
    - preset: Feature weight preset ("mood", "workout", "chill", "psychedelic")
    - use_genre_boost: Boost same-genre tracks (default: True)
    - use_artist_diversity: Limit songs per artist (default: True)
    """
    # First, look up the song info
    song_info = get_song_by_track_id(request.track_id)
    
    if not song_info:
        return SpotifyTrackResponse(
            track_id=request.track_id,
            found=False,
            track_name=None,
            track_artist=None,
            recommendations=[]
        )
    
    # Get similar songs with new parameters
    recommendations = get_similar_songs_by_track_id(
        request.track_id,
        request.top_n,
        preset=request.preset,
        use_genre_boost=request.use_genre_boost,
        use_artist_diversity=request.use_artist_diversity,
    )
    
    return SpotifyTrackResponse(
        track_id=request.track_id,
        found=True,
        track_name=song_info.get("track_name"),
        track_artist=song_info.get("track_artist"),
        recommendations=recommendations
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
