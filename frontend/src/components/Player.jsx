import { useEffect, useState } from "react";
import vinylImage from "../assets/images/vinyl.png";
import playButtonImage from "../assets/icons/play-button.png";
import pauseButtonImage from "../assets/icons/pause-button.png";
import skipButtonImage from "../assets/icons/skip-button.png";
import "./Player.css";

function formatTime(milliseconds) {
  if (!Number.isFinite(milliseconds) || milliseconds < 0) return "0:00";
  const totalSeconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  return `${minutes}:${String(totalSeconds % 60).padStart(2, "0")}`;
}

export default function Player({ currentTrack, recommendations = [], isPlaying, position, duration, onToggle, playerReady }) {
  const [livePosition, setLivePosition] = useState(position || 0);

  useEffect(() => {
    setLivePosition(position || 0);
    if (!isPlaying) return undefined;

    const startedAt = Date.now();
    const startingPosition = position || 0;
    const interval = window.setInterval(() => {
      setLivePosition(Math.min(startingPosition + (Date.now() - startedAt), duration || 0));
    }, 500);

    return () => window.clearInterval(interval);
  }, [position, isPlaying, duration]);

  const progress = duration ? Math.max(0, Math.min(100, (livePosition / duration) * 100)) : 0;
  const artwork = currentTrack?.album?.images?.[0]?.url;
  const title = currentTrack?.name || "Choose a song";
  const artists = currentTrack?.artists?.map((artist) => artist.name).join(", ") || "Your music will appear here";
  const currentTrackId = currentTrack?.uri?.replace("spotify:track:", "") || null;
  const currentRecommendation = recommendations.find((song) =>
    (song.track_id || song.id) === currentTrackId
  );
  const explanation = currentRecommendation?.explanation;

  return (
    <section className="player-area" aria-label="Now playing">
      <div className="now-playing">
        <div className="vinyl-progress-wrap">
          <div className={`vinyl-wrap ${isPlaying ? "vinyl-playing" : ""}`}>
            <div className="vinyl-disc">
              <img src={vinylImage} alt="Vinyl record" className="vinyl-image" />
              {artwork ? (
                <img src={artwork} alt="" className="vinyl-album-art" />
              ) : (
                <span className="vinyl-center-mark">E</span>
              )}
            </div>
          </div>
          <svg
            className="vinyl-semi-progress"
            viewBox="0 0 700 700"
            aria-label={`${Math.round(progress)}% played`}
          >
            <path
              className="vinyl-semi-progress-track"
              pathLength="100"
              d="M 350 50 A 300 300 0 0 1 640 450"
            />
            <path
              className="vinyl-semi-progress-fill"
              pathLength="100"
              d="M 350 50 A 300 300 0 0 1 640 450"

              style={{ strokeDashoffset: 100 - progress }}
            />
          </svg>
        </div>

        <div className="now-playing-details">
          <span className="now-playing-label">Now Playing</span>
          <h2>{title}</h2>
          <p>{artists}</p>
          {explanation && (
            <p className="now-playing-explanation">{explanation}</p>
          )}
          <div className="player-controls">
            <button
              type="button"
              className="skip-button skip-button-left"
              aria-label="Previous track"
            >
              <img src={skipButtonImage} alt="" />
            </button>
            <button
              type="button"
              className="main-play-button"
              onClick={onToggle}
              disabled={!playerReady}
              aria-label={isPlaying ? "Pause" : "Play"}
            >
              <img
                src={isPlaying ? pauseButtonImage : playButtonImage}
                alt=""
              />
            </button>
            <button
              type="button"
              className="skip-button skip-button-right"
              aria-label="Next track"
            >
              <img src={skipButtonImage} alt="" />
            </button>
          </div>

          <div className="progress-copy">
            <span>{formatTime(livePosition)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
