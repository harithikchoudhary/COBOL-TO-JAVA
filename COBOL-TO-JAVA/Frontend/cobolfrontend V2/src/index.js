import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";

// Debug: Log the current state of the document
console.log("Document ready state:", document.readyState);
console.log("Root element:", document.getElementById("root"));

// Create root element if it doesn't exist
const rootElement = document.getElementById("root");
if (!rootElement) {
  console.error("Root element not found, creating one...");
  const newRoot = document.createElement("div");
  newRoot.id = "root";
  document.body.appendChild(newRoot);
}

// Create React root and render
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
