import React, { useEffect, useState } from "react";
import axios from "axios";

const USERS_API_URL = "http://127.0.0.1:8001/users/?username=guest_user";
const CHAT_API_URL = "http://127.0.0.1:8001/api/chat";

const ChatWindow = () => {
  const [userId, setUserId] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [input, setInput] = useState("");
  const [chatHistory, setChatHistory] = useState([]);

  // Get user_id from FastAPI
  useEffect(() => {
    const fetchUserId = async () => {
      try {
        const res = await axios.post(USERS_API_URL);
        setUserId(res.data.user_id);
        console.log("Fetched user_id:", res.data.user_id);
      } catch (err) {
        console.error("Error getting user_id:", err);
      }
    };
    fetchUserId();
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || !userId) return;

    const newMessage = { role: "user", content: input };
    setChatHistory([...chatHistory, newMessage]);

    try {
      console.log("Sending to backend:", {
        user_id: userId,
        message: input,
        session_id: sessionId,
      });

      const res = await axios.post(CHAT_API_URL, {
        user_id: userId,
        message: input,
        session_id: sessionId,
      });

      setChatHistory([
        ...chatHistory,
        newMessage,
        { role: "assistant", content: res.data.response },
      ]);
      setSessionId(res.data.session_id); // Save session
      setInput("");
    } catch (err) {
      console.error("Error sending message:", err.response?.data || err.message);
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h2>Chat with AI</h2>
      <div
        style={{
          height: "300px",
          overflowY: "auto",
          border: "1px solid #ccc",
          padding: "10px",
          marginBottom: "10px",
        }}
      >
        {chatHistory.map((msg, i) => (
          <p key={i}>
            <strong>{msg.role}:</strong> {msg.content}
          </p>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type a message..."
        style={{ width: "80%", padding: "8px" }}
      />
      <button onClick={sendMessage} style={{ padding: "8px 16px", marginLeft: "10px" }}>
        Send
      </button>
    </div>
  );
};

export default ChatWindow;
