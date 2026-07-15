import { normalizeTextList } from "../utils/text.js";

export default function ResultsPage({ session, results, onStartNew }) {
  const patterns = normalizeTextList(results?.patterns || results?.state?.patterns);
  const recommendations = normalizeTextList(
    results?.recommendations || results?.state?.recommendations,
  );

  function handlePrint() {
    window.print();
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
          <button className="secondary-button" type="button" onClick={handlePrint}>
            Print
          </button>
          <button className="primary-button compact" type="button" onClick={onStartNew}>
            Start New Session
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
    </main>
  );
}
