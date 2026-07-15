import { useState } from "react";

import { postCreateChatSession } from "../api/client.js";

export default function WelcomePage({ onSessionReady }) {
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [message, setMessage] = useState("");

  const canCreate = name.trim().length > 0 && Number(age) > 0;

  async function handleCreateSession(event) {
    event.preventDefault();

    if (!canCreate || isCreating) {
      return;
    }

    setIsCreating(true);
    setMessage("Creating your session...");

    try {
      const payload = await postCreateChatSession({
        name: name.trim(),
        age: Number(age),
      });
      onSessionReady(payload);
    } catch (error) {
      setMessage(error.message || "The backend could not create a session yet.");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <main className="welcome-shell">
      <section className="welcome-card" aria-labelledby="welcome-title">
        <h1 id="welcome-title">Ethnography Assistant</h1>
        <p className="subtitle">Start with a few details, then continue in a guided chat.</p>

        <form onSubmit={handleCreateSession}>
          <label htmlFor="participant-name">Your Name</label>
          <input
            id="participant-name"
            type="text"
            placeholder="Enter your name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoComplete="name"
          />

          <label htmlFor="participant-age">Your Age</label>
          <input
            id="participant-age"
            type="number"
            placeholder="Enter your age"
            min="1"
            max="120"
            value={age}
            onChange={(event) => setAge(event.target.value)}
          />

          <button className="primary-button" type="submit" disabled={!canCreate || isCreating}>
            {isCreating ? "Creating..." : "Create Session"}
          </button>
        </form>

        <p className="status-text" aria-live="polite">
          {message}
        </p>
      </section>
    </main>
  );
}
