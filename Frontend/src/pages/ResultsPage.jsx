import { useState } from "react";

import { postDeleteCollection, postPatternAnalysis } from "../api/client.js";
import { buildPatternAnalysisRequest, normalizeResultsPayload } from "../utils/results.js";
import { clearSessionState, storeResults } from "../utils/session.js";
import { normalizeTextList } from "../utils/text.js";

export default function ResultsPage({ session, results, onEndSession, onResultsUpdate }) {
  const [isEnding, setIsEnding] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [message, setMessage] = useState("");
  const patterns = normalizeTextList(results?.patterns || results?.raw?.patterns);
  const recommendations = normalizeTextList(results?.recommendations || results?.raw?.recommendations);
  const resultsContext = {
    problem: results?.problem || results?.raw?.problem || "",
    domains: results?.domains || results?.raw?.domains || {},
  };

  async function handleEndSession() {
    if (isEnding) {
      return;
    }

    setIsEnding(true);
    setMessage("Ending session...");

    try {
      await postDeleteCollection({ session_id: session.session_id });
      clearSessionState();
      onEndSession();
    } catch {
      setMessage("The backend could not delete the session collection yet.");
    } finally {
      setIsEnding(false);
    }
  }

  function handlePrint() {
    window.print();
  }

  async function handleRegenerateResults() {
    if (isRegenerating || !resultsContext.problem) {
      return;
    }

    setIsRegenerating(true);
    setMessage("Regenerating patterns and recommendations...");

    try {
      const result = await postPatternAnalysis(buildPatternAnalysisRequest(session, resultsContext));
      const nextResults = normalizeResultsPayload(result, resultsContext);

      storeResults(nextResults);
      onResultsUpdate(nextResults);
      setMessage("Results regenerated.");
    } catch {
      setMessage("The backend could not regenerate results yet. Please try again.");
    } finally {
      setIsRegenerating(false);
    }
  }

  return (
    <main className="results-shell">
      <section className="results-hero">
        <div>
          <span>Ethnography Results</span>
          <h1>Patterns and Recommendations</h1>
          <p>{session.name}, here is what emerged from your interview.</p>
        </div>
        <div className="results-actions">
          <button
            className="secondary-action"
            type="button"
            onClick={handleRegenerateResults}
            disabled={isRegenerating || !resultsContext.problem}
          >
            {isRegenerating ? "Regenerating..." : "Regenerate Results"}
          </button>
          <button className="secondary-action" type="button" onClick={handlePrint}>
            Print Results
          </button>
          <button className="danger-button" type="button" onClick={handleEndSession} disabled={isEnding}>
            {isEnding ? "Ending..." : "End Session"}
          </button>
        </div>
      </section>

      <section className="results-grid">
        <article className="results-panel">
          <h2>Patterns</h2>
          {patterns.length > 0 ? (
            <div className="insight-list">
              {patterns.map((pattern, index) => (
                <p key={`pattern-${index}`}>{pattern}</p>
              ))}
            </div>
          ) : (
            <p className="muted-text">No strong patterns were returned.</p>
          )}
        </article>

        <article className="results-panel">
          <h2>Recommendations</h2>
          {recommendations.length > 0 ? (
            <div className="insight-list recommendation-list">
              {recommendations.map((recommendation, index) => (
                <p key={`recommendation-${index}`}>{recommendation}</p>
              ))}
            </div>
          ) : (
            <p className="muted-text">No recommendations were returned.</p>
          )}
        </article>
      </section>

      <p className="status-text" aria-live="polite">
        {message}
      </p>
    </main>
  );
}
