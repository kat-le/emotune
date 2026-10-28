
import { useState } from "react";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hey! Welcome to Emotune 🎵 How are you feeling today?",
      recommendations: [],
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSend(event) {
    event.preventDefault();

    if (!input.trim() || loading) return;

    const userMessage = {
      role: "user",
      content: input.trim(),
    };

    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:3001/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage.content,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Unable to get a response.");
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.reply,
          recommendations: data.recommendations || [],
        },
      ]);

    } catch (error) {
      console.error("Chat error:", error);

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            "Sorry! I'm having trouble responding right now. Please try again.",
          recommendations: [],
        },
      ]);

    } finally {
      setLoading(false);
    }
  }

  function SongCard({ song }) {
    const title =
      song.track_name || song.name || song.title || "Unknown song";

    const artist =
      song.track_artist || "Unknown artist";

    const trackId = song.track_id || song.id;

    const artwork =
      song.album_image ||
      song.album_art ||
      song.image_url ||
      song.image;

    const spotifyUrl = trackId
      ? `https://open.spotify.com/track/${trackId}`
      : null;

    return (
      <div className="song-card">
        <div className="song-artwork">
          {artwork ? (
            <img src={artwork} alt={`${title} album artwork`} />
          ) : (
            <span>🎵</span>
          )}
        </div>

        <div className="song-info">
          <h3>{title}</h3>
          <p>{artist}</p>

          {spotifyUrl && (
            <a
              href={spotifyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="spotify-link"
            >
              Listen on Spotify ↗
            </a>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="chat-header">
        <h1>Emotune 🎵</h1>
        <p>Your mood, your music.</p>
      </header>

      <main className="chat-container">
        <div className="messages">
          {messages.map((message, index) => (
            <div key={index} className={`message-group ${message.role}`}>
              <div className={`message ${message.role}`}>
                {message.content}
              </div>

              {message.recommendations?.length > 0 && (
                <div className="recommendations">
                  <h2>Recommended Songs 🎧</h2>

                  <div className="song-list">
                    {message.recommendations.map((song, songIndex) => (
                      <SongCard
                        key={song.track_id || song.id || songIndex}
                        song={song}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              Emotune is thinking...
            </div>
          )}
        </div>

        <form className="chat-input" onSubmit={handleSend}>
          <input
            type="text"
            placeholder="Tell Emotune how you're feeling..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={loading}
          />

          <button type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </main>
    </div>
  );
}

export default App;
