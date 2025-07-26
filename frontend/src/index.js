import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css'; // Make sure this CSS file exists
import App from './App'; // Make sure this component exists

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);