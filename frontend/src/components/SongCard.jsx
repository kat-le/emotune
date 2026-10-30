import "./SongCard.css";

export default function SongCard({
  song,
  isActive,
  isPlaying,
  playerReady,
  onPlay,
  onToggle,
}) {
  const title = song.track_name || song.name || song.title || "Unknown song";
  const artist = song.track_artist || song.artist || "Unknown artist";
  const trackId = song.track_id || song.id;
  const artwork = song.album_image || song.album_art || song.image_url || song.image;

  function handlePlayback() {
    if (!trackId) return;
    if (isActive) onToggle();
    else onPlay(trackId);
  }

  return (
    <article className="song-card">
      <div className="song-card-artwork">
        {artwork ? <img src={artwork} alt={`${title} album artwork`} /> : <span>♪</span>}
      </div>

      <div className="song-card-info">
        <h3>{title}</h3>
        <p>{artist}</p>
      </div>

      <button
        type="button"
        className="song-card-play"
        onClick={handlePlayback}
        disabled={!playerReady || !trackId}
        aria-label={isActive && isPlaying ? `Pause ${title}` : `Play ${title}`}
      >
        <span aria-hidden="true">{isActive && isPlaying ? "Ⅱ" : "▶"}</span>
      </button>
    </article>
  );
}
