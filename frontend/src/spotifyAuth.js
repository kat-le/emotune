
const CLIENT_ID = import.meta.env.VITE_SPOTIFY_CLIENT_ID;
const REDIRECT_URI = "http://127.0.0.1:5173/callback";

const SCOPES = [
  "streaming",
  "user-read-email",
  "user-read-private",
].join(" ");

const TOKEN_URL = "https://accounts.spotify.com/api/token";

// Generate a random string for PKCE.
function generateRandomString(length) {
  const possible =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

  const values = crypto.getRandomValues(new Uint8Array(length));

  return Array.from(values, (value) => possible[value % possible.length]).join("");
}

// Convert the verifier into a SHA-256 challenge.
async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);

  const digest = await crypto.subtle.digest("SHA-256", data);

  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

// Start Spotify login.
export async function loginWithSpotify() {
  if (!CLIENT_ID) {
    throw new Error("Missing Spotify Client ID.");
  }

  const verifier = generateRandomString(64);
  const challenge = await generateCodeChallenge(verifier);

  sessionStorage.setItem("spotify_code_verifier", verifier);

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: "code",
    redirect_uri: REDIRECT_URI,
    code_challenge_method: "S256",
    code_challenge: challenge,
    scope: SCOPES,
  });

  window.location.href =
    `https://accounts.spotify.com/authorize?${params.toString()}`;
}

// Exchange the authorization code for an access token.
export async function exchangeCodeForToken(code) {
  const verifier = sessionStorage.getItem("spotify_code_verifier");

  if (!verifier) {
    throw new Error("Spotify login session expired. Please log in again.");
  }

  const response = await fetch(TOKEN_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      client_id: CLIENT_ID,
      grant_type: "authorization_code",
      code,
      redirect_uri: REDIRECT_URI,
      code_verifier: verifier,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error_description || "Spotify login failed.");
  }

  sessionStorage.removeItem("spotify_code_verifier");

  saveTokens(data);

  return data.access_token;
}

// Save the tokens for this browser session.
function saveTokens(data) {
  sessionStorage.setItem("spotify_access_token", data.access_token);

  if (data.refresh_token) {
    sessionStorage.setItem("spotify_refresh_token", data.refresh_token);
  }

  const expiresAt = Date.now() + data.expires_in * 1000;

  sessionStorage.setItem("spotify_expires_at", String(expiresAt));
}

// Get a valid token, refreshing it when necessary.
export async function getSpotifyAccessToken() {
  const accessToken = sessionStorage.getItem("spotify_access_token");
  const expiresAt = Number(sessionStorage.getItem("spotify_expires_at"));

  if (accessToken && Date.now() < expiresAt - 60_000) {
    return accessToken;
  }

  const refreshToken = sessionStorage.getItem("spotify_refresh_token");

  if (!refreshToken) {
    return null;
  }

  const response = await fetch(TOKEN_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      client_id: CLIENT_ID,
      grant_type: "refresh_token",
      refresh_token: refreshToken,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    sessionStorage.removeItem("spotify_access_token");
    sessionStorage.removeItem("spotify_refresh_token");
    sessionStorage.removeItem("spotify_expires_at");

    throw new Error(data.error_description || "Unable to refresh Spotify token.");
  }

  saveTokens(data);

  return data.access_token;
}

// Clear the saved Spotify login.
export function logoutFromSpotify() {
  sessionStorage.removeItem("spotify_access_token");
  sessionStorage.removeItem("spotify_refresh_token");
  sessionStorage.removeItem("spotify_expires_at");
  sessionStorage.removeItem("spotify_code_verifier");
}
