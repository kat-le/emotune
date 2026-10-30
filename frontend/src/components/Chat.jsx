import { useEffect, useRef, useState } from "react";
import "./Chat.css";

export default function Chat({ onRecommendations }) {
  const [open, setOpen] = useState(true);
  const messagesRef = useRef(null);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hey! Welcome to Emotune 🎵 How are you feeling today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages, loading, open]);

  async function handleSend(event) {
    event.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = { role: "user", content: input.trim() };
    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:3001/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage.content }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Unable to get a response.");
      }

      const recommendations = data.recommendations || [];
      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: data.reply },
      ]);
      onRecommendations(recommendations);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: "Sorry! I'm having trouble responding right now. Please try again.",
        },
      ]);
      onRecommendations([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside className={`chat-panel ${open ? "chat-panel-open" : "chat-panel-closed"}`} aria-label="Emotune chat">
      {open ? (
        <>
          <div className="chat-title">
            <span className="chat-title-mark">✦</span>
            <div>
              <p>Emotune</p>
              <span>AI music companion</span>
            </div>
            <button
              type="button"
              className="chat-close"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              −
            </button>
          </div>

          <div className="chat-messages" ref={messagesRef}>
            {messages.map((message, index) => (
              <div key={index} className={`chat-message chat-message-${message.role}`}>
                {message.content}
              </div>
            ))}
            {loading && <div className="chat-message chat-message-assistant">Thinking...</div>}
          </div>

          <form className="chat-input" onSubmit={handleSend}>
            <input
              type="text"
              placeholder="How are you feeling?"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              disabled={loading}
            />
            <button type="submit" disabled={loading || !input.trim()} aria-label="Send message">
              ↑
            </button>
          </form>
        </>
      ) : (
        <button type="button" className="chat-open-button" onClick={() => setOpen(true)}>
          <span>✦</span>
          <span>Open chat</span>
        </button>
      )}
    </aside>
  );
}
