import { useEffect, useRef, useState } from "react";

import { postChatMessage, postChatResults } from "../api/client.js";

function isAssistant(message) {
  return message.role === "assistant";
}

export default function ChatPage({ session, chatState, onStateChange, onResults, onStartNew }) {
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [status, setStatus] = useState("");
  const bottomRef = useRef(null);
  const hasRequestedResults = useRef(false);

  const messages = chatState?.conversation || [];
  const isReadyForResults = chatState?.stage === "ready_for_results";
  const canSend = draft.trim().length > 0 && !isSending && !isGenerating && !isReadyForResults;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, status]);

  useEffect(() => {
    if (!isReadyForResults || hasRequestedResults.current) {
      return;
    }

    hasRequestedResults.current = true;
    handleGenerateResults();
  }, [isReadyForResults]);

  async function handleSubmit(event) {
    event.preventDefault();

    if (!canSend) {
      return;
    }

    const message = draft.trim();
    setDraft("");
    setIsSending(true);
    setStatus("Thinking...");

    try {
      const payload = await postChatMessage({
        state: chatState,
        message,
      });
      onStateChange(payload.state);
      setStatus(payload.stage === "ready_for_results" ? "Generating recommendations..." : "");
    } catch (error) {
      setStatus(error.message || "The message could not be sent.");
      setDraft(message);
    } finally {
      setIsSending(false);
    }
  }

  async function handleGenerateResults() {
    if (isGenerating) {
      return;
    }

    setIsGenerating(true);
    setStatus("Generating patterns and recommendations...");

    try {
      const payload = await postChatResults({ state: chatState });
      onResults(payload);
    } catch (error) {
      hasRequestedResults.current = false;
      setStatus(error.message || "The results could not be generated yet.");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <main className="chat-shell">
      <header className="chat-header">
        <div>
          <span>Ethnography Assistant</span>
          <h1>Chat Interview</h1>
        </div>
        <div className="chat-session">
          <strong>{session.name}</strong>
          <small>{session.session_id}</small>
        </div>
      </header>

      <section className="chat-window" aria-label="Chat conversation">
        {messages.map((message, index) => (
          <article
            className={`chat-bubble ${isAssistant(message) ? "assistant" : "user"}`}
            key={`${message.role}-${index}`}
          >
            <span>{isAssistant(message) ? "Assistant" : "You"}</span>
            <p>{message.content}</p>
          </article>
        ))}

        {(isSending || isGenerating) && (
          <article className="chat-bubble assistant thinking">
            <span>Assistant</span>
            <p>{isGenerating ? "Preparing your recommendations..." : "Thinking..."}</p>
          </article>
        )}

        <div ref={bottomRef} />
      </section>

      {isReadyForResults ? (
        <section className="chat-complete-panel">
          <div>
            <h2>Interview complete</h2>
            <p>{status || "Your patterns and recommendations are being prepared."}</p>
          </div>
          <button className="primary-button compact" type="button" onClick={handleGenerateResults} disabled={isGenerating}>
            {isGenerating ? "Generating..." : "Generate Results"}
          </button>
        </section>
      ) : (
        <form className="chat-composer" onSubmit={handleSubmit}>
          <textarea
            aria-label="Message"
            placeholder="Type your answer here..."
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows="2"
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <button className="send-button" type="submit" disabled={!canSend}>
            Send
          </button>
        </form>
      )}

      <footer className="chat-footer">
        <p className="status-text" aria-live="polite">
          {status}
        </p>
        <button className="text-button" type="button" onClick={onStartNew}>
          Start New Session
        </button>
      </footer>
    </main>
  );
}
