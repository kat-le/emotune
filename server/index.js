import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { GoogleGenAI } from "@google/genai";

dotenv.config();

const app = express();

app.use(cors({
  origin: "http://127.0.0.1:5173",
}));

app.use(express.json());

const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
});

const MODEL = process.env.GEMINI_MODEL || "gemini-3.5-flash-lite";
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";


let spotifyAccessToken = null;
let spotifyTokenExpiresAt = 0;

async function getSpotifyAccessToken() {
  // Reuse the token until it is close to expiring.
  if (
    spotifyAccessToken &&
    Date.now() < spotifyTokenExpiresAt
  ) {
    return spotifyAccessToken;
  }

  const clientId = process.env.SPOTIFY_CLIENT_ID;
  const clientSecret = process.env.SPOTIFY_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    throw new Error("Spotify credentials are missing from server/.env");
  }

  const credentials = Buffer.from(
    `${clientId}:${clientSecret}`
  ).toString("base64");

  const response = await fetch(
    "https://accounts.spotify.com/api/token",
    {
      method: "POST",
      headers: {
        Authorization: `Basic ${credentials}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        grant_type: "client_credentials",
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Unable to authenticate with Spotify.");
  }

  const data = await response.json();

  spotifyAccessToken = data.access_token;

  // Refresh one minute before the token expires.
  spotifyTokenExpiresAt =
    Date.now() + (data.expires_in - 60) * 1000;

  return spotifyAccessToken;
}


async function getSpotifyTrackDetails(trackId, accessToken) {
  if (!trackId) return {};

  try {
    const response = await fetch(
      `https://api.spotify.com/v1/tracks/${encodeURIComponent(trackId)}?market=US`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );

    if (!response.ok) {
      console.error(
        `Spotify track lookup failed for ${trackId}:`,
        response.status
      );
      return {};
    }

    const track = await response.json();

    return {
      album_image: track.album?.images?.[0]?.url || null,
      spotify_url: track.external_urls?.spotify || null,
    };

  } catch (error) {
    console.error("Spotify artwork lookup error:", error);
    return {};
  }
}

async function addAlbumArtwork(recommendations) {
  if (!recommendations?.length) return [];

  try {
    const accessToken = await getSpotifyAccessToken();

    return await Promise.all(
      recommendations.map(async (song) => {
        const spotifyDetails = await getSpotifyTrackDetails(
          song.track_id,
          accessToken
        );

        return {
          ...song,
          ...spotifyDetails,
        };
      })
    );

  } catch (error) {
    console.error("Unable to retrieve Spotify artwork:", error);

    // Keep recommendations working even if Spotify is unavailable.
    return recommendations;
  }
}

const systemInstruction = `
You are Emotune, a friendly K-pop music recommendation assistant.
Help users discover songs based on their emotions, moods, and music preferences.
You have access to real song recommendations from the Emotune database.
When a user asks for recommendations, use the appropriate function.
Never invent song titles or artists.
SUPPORTED REQUESTS:
You may ONLY recommend songs using:
1. Mood-based recommendations.
2. Similar-song recommendations.

Do NOT recommend songs based on:
- A specific artist or group.
- A specific album.
- A genre or category alone.
- Release date, popularity, or chart rankings.
- Requests to list songs by an artist.

If a request does not fit one of the two supported types:
- Do not call any function.
- Do not invent or generate song recommendations.
- Politely explain that Emotune currently supports mood-based
  and similar-song recommendations only.
- Suggest an example of a supported request.

Supported moods are:
happy, sad, energetic, calm, romantic, focus, nostalgic.

For emotional-context requests, understand the user's message and choose
a suitable supported desired mood. If their desired mood is unclear,
ask a follow-up question.

After receiving recommendations, explain the results in a friendly,
conversational way. 
When recommending songs, do not list song titles or artist names in your text response.

The application displays recommendations separately as song cards.
Instead, provide a short, friendly introduction to the recommendations.

For example:
"Here are 10 songs that match your mood! 🎵"

Never repeat the song recommendations in a numbered list or bullet list.
Only recommend songs returned by the functions. 
Unless the user requests a different number, always recommend 10 songs.
`;

const tools = [
  {
    functionDeclarations: [
      {
        name: "recommend_by_mood",
        description: "Get K-pop song recommendations for a specific mood.",
        parameters: {
          type: "OBJECT",
          properties: {
            mood: {
              type: "STRING",
              enum: [
                "happy",
                "sad",
                "energetic",
                "calm",
                "romantic",
                "focus",
                "nostalgic"
              ],
              description: "The mood to recommend songs for."
            },
            top_n: {
              type: "INTEGER",
              description: "Number of songs to return. Default: 10, maximum: 20."
            }
          },
          required: ["mood"]
        }
      },
      {
        name: "recommend_for_emotional_context",
        description:
          "Recommend songs based on what the user says they are feeling and the mood they want to move toward.",
        parameters: {
          type: "OBJECT",
          properties: {
            text: {
              type: "STRING",
              description: "The user's description of their emotional context."
            },
            desired_mood: {
              type: "STRING",
              enum: [
                "happy",
                "sad",
                "energetic",
                "calm",
                "romantic",
                "focus",
                "nostalgic"
              ],
              description: "The mood the user wants music for."
            },
            current_mood: {
              type: "STRING",
              description: "The user's current mood, if known."
            },
            intensity: {
              type: "INTEGER",
              description: "Emotional intensity from 1 to 5."
            },
            top_n: {
              type: "INTEGER",
              description: "Number of songs to return. Default: 10, maximum: 20."
            }
          },
          required: ["text", "desired_mood"]
        }
      },
      {
        name: "get_similar_songs",
        description: "Find songs similar to a song in the Emotune dataset.",
        parameters: {
          type: "OBJECT",
          properties: {
            song_name: {
              type: "STRING",
              description: "The name of the song to find similar songs for."
            },
            top_n: {
              type: "INTEGER",
              description: "Number of songs to return. Default: 10, maximum: 20."
            },
            preset: {
              type: "STRING",
              enum: ["mood", "workout", "chill", "psychedelic"],
              description: "Optional similarity preference."
            }
          },
          required: ["song_name"]
        }
      }
    ]
  }
];

async function callEmotuneFunction(name, args) {
  let endpoint;
  let body;

  const topN = Math.min(Math.max(Number(args.top_n) || 10, 1), 20);

  if (name === "recommend_by_mood") {
    endpoint = "/api/recommend/text";
    body = {
      mood: args.mood,
      top_n: topN
    };
  } else if (name === "recommend_for_emotional_context") {
    endpoint = "/api/recommend/text";
    body = {
      text: args.text,
      current_mood: args.current_mood || null,
      desired_mood: args.desired_mood,
      intensity: args.intensity || 3,
      top_n: topN
    };
  } else if (name === "get_similar_songs") {
    endpoint = "/api/recommend/similar";
    body = {
      song_name: args.song_name,
      top_n: topN,
      preset: args.preset || null
    };
  } else {
    throw new Error(`Unknown function: ${name}`);
  }

  const backendResponse = await fetch(`${BACKEND_URL}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });

  const result = await backendResponse.json();

  if (!backendResponse.ok) {
    throw new Error(
      result.detail || result.error || "The recommendation request failed."
    );
  }

  return result;
}

app.get("/api/health", (req, res) => {
  res.json({
    status: "Emotune server is running!"
  });
});

app.get("/api/test-gemini", async (req, res) => {
  try {
    const response = await ai.models.generateContent({
      model: MODEL,
      contents: "Say hello to Emotune!"
    });

    res.json({
      success: true,
      message: response.text
    });
  } catch (error) {
    console.error("Gemini error:", error);

    res.status(500).json({
      success: false,
      error: "Unable to connect to Gemini."
    });
  }
});

app.post("/api/chat", async (req, res) => {
  try {
    const { message } = req.body;

    if (typeof message !== "string" || !message.trim()) {
      return res.status(400).json({
        success: false,
        error: "Please enter a message."
      });
    }

    const config = {
      systemInstruction,
      tools
    };

    // First, let Gemini decide whether it needs a recommendation function.
    const response = await ai.models.generateContent({
      model: MODEL,
      contents: message,
      config
    });

    const functionCall = response.functionCalls?.[0];

    // If Gemini did not request a function, return its conversational reply.
    if (!functionCall) {
      return res.json({
        success: true,
        reply: response.text
      });
    }

    // Execute the function using the existing Python backend.
    const functionResult = await callEmotuneFunction(
      functionCall.name,
      functionCall.args || {}
    );

    // Send the function result back to Gemini so it can explain the songs.
    const finalResponse = await ai.models.generateContent({
      model: MODEL,
      contents: [
        {
          role: "user",
          parts: [{ text: message }]
        },
        response.candidates[0].content,
        {
          role: "user",
          parts: [
            {
              functionResponse: {
                name: functionCall.name,
                response: functionResult
              }
            }
          ]
        }
      ],
      config: {
        systemInstruction
      }
    });

    // const recommendationsWithArtwork = await addAlbumArtwork(
    //     functionResult.recommendations || []
    // );

    // res.json({
    //     success: true,
    //     reply: finalResponse.text,
    //     recommendations: recommendationsWithArtwork
    // });

    res.json({
      success: true,
      reply: finalResponse.text,
      recommendations: functionResult.recommendations || []
    });
  } catch (error) {
    console.error("Chat error:", error);

    res.status(500).json({
      success: false,
      error: error.message || "Something went wrong while generating your response."
    });
  }
});

const PORT = 3001;

app.listen(PORT, () => {
  console.log(`Emotune server running at http://localhost:${PORT}`);
});
