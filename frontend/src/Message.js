import React from 'react';
import './Message.css';

function Message({ message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`message-container ${isUser ? 'user-message' : 'ai-message'}`}>
      <div className="message-content">
        <p>{message.content}</p>
      </div>
    </div>
  );
}

export default Message;