import { useEffect, useRef, useState } from "react";
import Chat from "./components/Chat";
import Player from "./components/Player";
import Recommendations from "./components/Recommendations";
import {
  loginWithSpotify,
  exchangeCodeForToken,
  getSpotifyAccessToken,
} from "./spotifyAuth";
import "./App.css";

export default function App() {
  const spotifyPlayer = useRef(null);
  const spotifyCallbackHandled = useRef(false);
  const spotifyRateLimitUntil = useRef(0);

  const [spotifyDeviceId, setSpotifyDeviceId] = useState(null);
  const [spotifyStatus, setSpotifyStatus] = useState("Disconnected");
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [recommendations, setRecommendations] = useState([]);
  const [spotifyAccessToken, setSpotifyAccessToken] = useState(
    () => sessionStorage.getItem("spotify_access_token")
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const error = params.get("error");

    if (error) {
      setSpotifyStatus(`Spotify authorization failed: ${error}`);
      window.history.replaceState({}, document.title, "/");
      return;
    }

    if (!code || spotifyCallbackHandled.current) return;
    spotifyCallbackHandled.current = true;

    async function handleCallback() {
      try {
        setSpotifyStatus("Completing Spotify login...");
        await exchangeCodeForToken(code);
        setSpotifyAccessToken(sessionStorage.getItem("spotify_access_token"));
        setSpotifyStatus("Spotify login successful!");
        window.history.replaceState({}, document.title, "/");
      } catch (callbackError) {
        console.error("Spotify login error:", callbackError);
        setSpotifyStatus("Spotify login failed");
      }
    }

    handleCallback();
  }, []);

  useEffect(() => {
    if (!spotifyAccessToken) {
      setSpotifyStatus("Connect Spotify to use the player");
      return undefined;
    }

    let playerInstance = null;
    let disposed = false;

    const createPlayer = () => {
      if (disposed || !window.Spotify || spotifyPlayer.current) return;

      const player = new window.Spotify.Player({
        name: "Emotune Web Player",
        getOAuthToken: async (callback) => {
          try {
            const token = await getSpotifyAccessToken();
            if (token) callback(token);
            else setSpotifyStatus("Please connect Spotify");
          } catch (tokenError) {
            console.error("Unable to refresh Spotify token:", tokenError);
            setSpotifyStatus("Spotify authentication failed");
          }
        },
        volume: 0.5,
      });

      playerInstance = player;
      spotifyPlayer.current = player;

      player.addListener("ready", ({ device_id }) => {
        setSpotifyDeviceId(device_id);
        setSpotifyStatus("Connected to Spotify");
      });
      player.addListener("not_ready", () => {
        setSpotifyDeviceId(null);
        setSpotifyStatus("Player disconnected");
      });
      player.addListener("player_state_changed", (state) => {
        const track = state?.track_window?.current_track || null;
        setCurrentTrack(track);
        setIsPlaying(state ? !state.paused : false);
        setPosition(state?.position || 0);
        setDuration(state?.duration || track?.duration_ms || 0);
      });
      player.addListener("initialization_error", ({ message }) => {
        console.error("Spotify initialization error:", message);
        setSpotifyStatus("Initialization error");
      });
      player.addListener("authentication_error", ({ message }) => {
        console.error("Spotify authentication error:", message);
        setSpotifyStatus("Authentication error");
      });
      player.addListener("account_error", ({ message }) => {
        console.error("Spotify account error:", message);
        setSpotifyStatus("Premium account required");
      });

      player.connect().then((connected) => {
        setSpotifyStatus(connected ? "Connecting to Spotify..." : "Could not connect to Spotify");
      });
    };

    if (window.Spotify) createPlayer();
    else {
      window.onSpotifyWebPlaybackSDKReady = createPlayer;
      if (!document.querySelector('script[src="https://sdk.scdn.co/spotify-player.js"]')) {
        const script = document.createElement("script");
        script.src = "https://sdk.scdn.co/spotify-player.js";
        script.async = true;
        document.body.appendChild(script);
      }
    }

    return () => {
      disposed = true;
      if (playerInstance) playerInstance.disconnect();
      if (spotifyPlayer.current === playerInstance) spotifyPlayer.current = null;
    };
  }, [spotifyAccessToken]);

  async function togglePlayback() {
    if (!spotifyPlayer.current) return;
    await spotifyPlayer.current.togglePlay();
  }

  async function playSpotifyTrack(trackId) {
    if (!spotifyDeviceId || !spotifyPlayer.current || !trackId) {
      setSpotifyStatus("Waiting for Spotify player to connect");
      return;
    }

    const remainingCooldown = spotifyRateLimitUntil.current - Date.now();
    if (remainingCooldown > 0) {
      setSpotifyStatus(`Rate limited; try again in ${Math.ceil(remainingCooldown / 1000)}s`);
      return;
    }

    const accessToken = await getSpotifyAccessToken();
    if (!accessToken) {
      setSpotifyStatus("Please connect Spotify");
      return;
    }

    await spotifyPlayer.current.activateElement?.();

    try {
      const response = await fetch(
        `https://api.spotify.com/v1/me/player/play?device_id=${spotifyDeviceId}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ uris: [`spotify:track:${trackId}`] }),
        }
      );

      if (response.ok || response.status === 204) {
        setSpotifyStatus("Playback started");
        return;
      }

      const responseText = await response.text().catch(() => "");
      if (response.status === 429) {
        const retryAfter = Number.parseInt(response.headers.get("Retry-After") || "", 10);
        const waitSeconds = Number.isFinite(retryAfter) ? Math.max(retryAfter, 1) : 60;
        spotifyRateLimitUntil.current = Date.now() + waitSeconds * 1000;
        setSpotifyStatus(`Rate limited; try again in ${waitSeconds}s`);
      } else {
        console.error("Spotify playback error:", response.status, responseText);
        setSpotifyStatus(`Playback failed (${response.status})`);
      }
    } catch (error) {
      console.error("Unable to start playback:", error);
      setSpotifyStatus("Unable to start playback");
    }
  }

  const playerReady = Boolean(spotifyDeviceId);

  function connectSpotify() {
    loginWithSpotify().catch((error) => {
      console.error(error);
      setSpotifyStatus("Unable to start Spotify login");
    });
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">E</span>
          <div>
            <h1>emotune</h1>
            <p>music for every feeling</p>
          </div>
        </div>

        {!spotifyAccessToken ? (
          <button className="connect-button" type="button" onClick={connectSpotify}>
            Connect Spotify
          </button>
        ) : (
          <span className="spotify-status">{spotifyStatus}</span>
        )}
      </header>

      <main className="main-rectangle">
        <div className="playback-status-line">
          <span className="status-dot" />
          <span>{spotifyStatus}</span>
        </div>

        <div className="app-grid">
          <Player
            currentTrack={currentTrack}
            isPlaying={isPlaying}
            position={position}
            duration={duration}
            onToggle={togglePlayback}
            playerReady={playerReady}
          />

          <Recommendations
            songs={recommendations}
            currentTrack={currentTrack}
            isPlaying={isPlaying}
            playerReady={playerReady}
            onPlay={playSpotifyTrack}
            onToggle={togglePlayback}
          />
        </div>

        <Chat onRecommendations={setRecommendations} />
      </main>
    </div>
  );
}
