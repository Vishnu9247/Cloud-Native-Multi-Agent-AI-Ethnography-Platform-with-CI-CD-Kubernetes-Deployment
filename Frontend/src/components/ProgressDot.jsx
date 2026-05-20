export default function ProgressDot({ isComplete }) {
  return <span className={`progress-dot${isComplete ? " is-complete" : ""}`} aria-hidden="true" />;
}
