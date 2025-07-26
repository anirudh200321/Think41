import React from 'react';
import Message from './Message';
import './MessageList.css';

function MessageList({ messages }) {
  return (
    <div className="message-list-container">
      {messages.map((message, index) => (
        <Message key={index} message={message} />
      ))}
    </div>
  );
}

export default MessageList;