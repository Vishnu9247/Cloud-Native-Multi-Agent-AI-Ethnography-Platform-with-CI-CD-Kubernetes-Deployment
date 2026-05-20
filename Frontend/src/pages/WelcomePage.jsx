import { useState } from "react";

import { postJson } from "../api/client.js";
import { makeSessionId, storeSession } from "../utils/session.js";

export default function WelcomePage({ onSessionReady }) {
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [session, setSession] = useState(null);
  const [syncMessage, setSyncMessage] = useState("");
  const [isSyncing, setIsSyncing] = useState(false);

  const canCreate = name.trim().length > 0 && Number(age) > 0;

  async function handleCreateSession(event) {
    event.preventDefault();

    if (!canCreate) {
      return;
    }

    const nextSession = {
      name: name.trim(),
      age: Number(age),
      session_id: makeSessionId(name),
    };

    setSession(nextSession);
    storeSession(nextSession);
    setSyncMessage("");
    setIsSyncing(true);

    try {
      await postJson("/vector/create", { session_id: nextSession.session_id });
      setSyncMessage("Session synced with the backend.");
    } catch {
      setSyncMessage("Session created locally. Start the backend to sync it.");
    } finally {
      setIsSyncing(false);
    }
  }

  if (session) {
    return (
      <main className="welcome-shell">
        <section className="welcome-card" aria-labelledby="welcome-title">
          <h1 id="welcome-title">Ethnography Assistant</h1>
          <p className="subtitle">Welcome! Let's get started with your session.</p>

          <div className="session-id-panel">
            <span>Session ID:</span>
            <strong>{session.session_id}</strong>
          </div>

          <div className="person-summary">
            <p>
              <strong>Name:</strong> {session.name}
            </p>
            <p>
              <strong>Age:</strong> {session.age}
            </p>
          </div>

          <button className="start-button" type="button" onClick={() => onSessionReady(session)}>
            Let's Start
          </button>

          <p className="status-text" aria-live="polite">
            {isSyncing ? "Creating backend session..." : syncMessage}
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="welcome-shell">
      <section className="welcome-card" aria-labelledby="welcome-title">
        <h1 id="welcome-title">Ethnography Assistant</h1>
        <p className="subtitle">Welcome! Let's get started with your session.</p>

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

          <button className="create-button" type="submit" disabled={!canCreate}>
            Create Session
          </button>
        </form>
      </section>
    </main>
  );
}
