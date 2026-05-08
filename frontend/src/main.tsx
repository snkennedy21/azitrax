import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return (
    <main className="app-shell">
      <section className="intro">
        <p className="eyebrow">Vector</p>
        <h1>Minimal geospatial app</h1>
        <p>
          React is running locally. Map interactions will arrive in a later
          slice.
        </p>
      </section>
    </main>
  );
}

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element not found");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
