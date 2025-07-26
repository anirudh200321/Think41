import React, { useState, useEffect } from 'react';
import MessageList from './MessageList';
import UserInput from './UserInput';
import axios from 'axios';
import './ChatWindow.css';

const CHAT_API_URL = 'http://127.0.0.1:8001/api/chat';
const USERS_API_URL = 'http://127.0.0.1:8001/users/';

function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [userId, setUserId] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const createOrGetUserId = async () => {
      try {
        const response = await axios.post(`${USERS_API_URL}?username=guest_user`);
        setUserId(response.data.id);
        console.log('User created:', response.data.id);
      } catch (error) {
        console.error('Error creating user:', error);
      }
    };
    if (!userId) {
      createOrGetUserId();
    }
  }, [userId]);

  const handleSendMessage = async (messageContent) => {
    if (!userId) {
      console.error('User ID not available.');
      return;
    }

    const userMessage = { role: 'user', content: messageContent };
    setMessages(prevMessages => [...prevMessages, userMessage]);
    setIsLoading(true);

    try {
      const payload = {
        user_id: userId,
        message: messageContent,
        session_id: sessionId
      };
      
      const response = await axios.post(CHAT_API_URL, payload);
      
      setSessionId(response.data.session_id);
      const aiMessage = { role: 'assistant', content: response.data.response };
      setMessages(prevMessages => [...prevMessages, aiMessage]);

    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' };
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-window">
      <header className="chat-header">
        <h1>AI Assistant</h1>
      </header>
      <MessageList messages={messages} />
      <UserInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}

export default ChatWindow;