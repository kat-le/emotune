
import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { GoogleGenAI } from "@google/genai";

dotenv.config();

const app = express();

app.use(cors({
  origin: "http://localhost:5173",
}));

app.use(express.json());

const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
});

const MODEL = process.env.GEMINI_MODEL || "gemini-3.5-flash-lite";
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const systemInstruction = `
You are Emotune, a friendly K-pop music recommendation assistant.

Help users discover songs based on their emotions, moods, and music preferences.

You have access to real song recommendations from the Emotune database.
When a user asks for recommendations, use the appropriate function.
Never invent song titles or artists.

Supported moods are:
happy, sad, energetic, calm, romantic, focus, nostalgic.

For emotional-context requests, understand the user's message and choose
a suitable supported desired mood. If their desired mood is unclear,
ask a follow-up question.

After receiving recommendations, explain the results in a friendly,
conversational way. Only recommend songs returned by the functions. 
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
