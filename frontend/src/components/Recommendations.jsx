import SongCard from "./SongCard";
import "./Recommendations.css";

export default function Recommendations({
  songs,
  meta,
  currentTrack,
  isPlaying,
  playerReady,
  onPlay,
  onToggle,
}) {
  const activeId = currentTrack?.uri?.replace("spotify:track:", "") || null;
  const description = meta?.type === "mood"
    ? `${meta.mood || "Mood"} Playlist`
    : meta?.type === "similar"
      ? `For ${meta.sourceSong.title} by ${meta.sourceSong.artist}`
      : "";

  return (
    <aside className="recommendations-panel" aria-label="Song recommendations">
      <div className="recommendations-heading">
        <div>
          <span>DISCOVER</span>
          <h2>Recommendations</h2>
        </div>
        <span className="recommendation-count">{songs.length}</span>
      </div>
      <div className="recommendations-description"><p>{description}</p></div>
      <div className="recommendations-list">
        {songs.map((song, index) => {
          const trackId = song.track_id || song.id;
          return (
            <SongCard
              key={trackId || index}
              song={song}
              isActive={trackId === activeId}
              isPlaying={isPlaying}
              playerReady={playerReady}
              onPlay={onPlay}
              onToggle={onToggle}
            />
          );
        })}
      </div>
    </aside>
  );
}
