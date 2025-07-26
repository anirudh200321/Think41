import React, { useState } from 'react';
import './UserInput.css';

function UserInput({ onSendMessage }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="user-input-form">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type your message..."
        className="user-input-field"
      />
      <button type="submit" className="send-button">Send</button>
    </form>
  );
}

export default UserInput;