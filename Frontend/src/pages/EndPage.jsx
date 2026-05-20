export default function EndPage({ onStartNew }) {
  return (
    <main className="welcome-shell">
      <section className="end-card">
        <span>Session Ended</span>
        <h1>Thank you for sharing your experience.</h1>
        <p>Your session has been closed. You can start again whenever you are ready.</p>
        <button className="primary-action" type="button" onClick={onStartNew}>
          Start New Session
        </button>
      </section>
    </main>
  );
}
