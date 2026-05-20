import ProgressDot from "./ProgressDot.jsx";

export default function DomainTimeline({ items }) {
  if (!items.length) {
    return <p className="empty-domains">No domains were returned yet.</p>;
  }

  return (
    <ol className="domain-timeline">
      {items.map((item, index) => (
        <li className={`timeline-item ${item.type}${item.isComplete ? " is-complete" : ""}`} key={item.id}>
          <span
            className={`timeline-rail${index === items.length - 1 ? " is-last" : ""}${
              item.isComplete ? " is-complete" : ""
            }`}
            aria-hidden="true"
          >
            <ProgressDot isComplete={item.isComplete} />
          </span>
          <span className="timeline-label">{item.label}</span>
        </li>
      ))}
    </ol>
  );
}
