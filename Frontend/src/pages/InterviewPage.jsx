import { useMemo, useState } from "react";

import {
  postAddProblem,
  postDomainSelection,
  postProblemFraming,
  postSessionDetails,
} from "../api/client.js";
import { extractRawDomains, normalizeDomains } from "../utils/domains.js";
import { storeExploration } from "../utils/session.js";
import { getLatestAssistantMessage, isCompletionMessage } from "../utils/text.js";

export default function InterviewPage({ session, onBack, onExplore }) {
  const [problem, setProblem] = useState("");
  const [conversation, setConversation] = useState([]);
  const [agentState, setAgentState] = useState(null);
  const [hasStoredProblem, setHasStoredProblem] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSelectingDomains, setIsSelectingDomains] = useState(false);
  const [message, setMessage] = useState("");
  const isComplete = Boolean(agentState?.is_complete);
  const assistantMessage = getLatestAssistantMessage(conversation);
  const framedProblem =
    agentState?.summary || conversation.find((messageItem) => messageItem.role === "user")?.content || "";

  const greetingName = useMemo(() => {
    return session.name.charAt(0).toUpperCase() + session.name.slice(1);
  }, [session.name]);

  async function handleSubmit(event) {
    event.preventDefault();

    if (!problem.trim()) {
      return;
    }

    setIsSubmitting(true);
    setMessage("");

    const nextConversation = [
      ...conversation,
      {
        role: "user",
        content: problem.trim(),
      },
    ];

    setConversation(nextConversation);
    setProblem("");

    try {
      if (!hasStoredProblem) {
        await Promise.all([
          postAddProblem({
            session_id: session.session_id,
            problem: problem.trim(),
          }),
          postSessionDetails({
            session_id: session.session_id,
            name: session.name,
            age: Number(session.age),
            problem: problem.trim(),
          }),
        ]);
        setHasStoredProblem(true);
      }

      const result = await postProblemFraming({
        session_id: session.session_id,
        name: session.name,
        age: String(session.age),
        problem_conversation: nextConversation,
        summary: agentState?.summary || "",
        is_complete: Boolean(agentState?.is_complete),
      });

      const resultConversation = result?.problem_conversation || nextConversation;
      const hasCompletionMessage = resultConversation.some((item) => isCompletionMessage(item.content));
      const normalizedResult = hasCompletionMessage
        ? {
            ...result,
            is_complete: true,
            problem_conversation: resultConversation.filter((item) => !isCompletionMessage(item.content)),
          }
        : result;
      const returnedConversation = normalizedResult?.problem_conversation || nextConversation;
      setConversation(returnedConversation);
      setAgentState(normalizedResult);

      if (normalizedResult?.is_complete) {
        setMessage("Your problem framing is complete. You can move to exploration.");
      } else {
        setMessage("Please answer the follow-up questions so I can understand the problem better.");
      }
    } catch {
      setMessage("The backend did not accept the problem yet. Please check the agent route and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleExplore() {
    if (!isComplete || isSelectingDomains) {
      return;
    }

    setIsSelectingDomains(true);
    setMessage("Selecting domains to explore...");

    try {
      const result = await postDomainSelection({
        session_id: session.session_id,
        problem: framedProblem,
        domains: {},
      });
      const rawDomains = extractRawDomains(result);
      const exploration = {
        summary: agentState?.summary || "",
        problem: framedProblem,
        rawDomains,
        domains: normalizeDomains(rawDomains),
        raw: result,
      };

      storeExploration(exploration);
      onExplore(exploration);
    } catch {
      setMessage("The backend did not return domains yet. Please check the domain-selection route.");
    } finally {
      setIsSelectingDomains(false);
    }
  }

  return (
    <main className="interview-shell">
      <section className="interview-panel" aria-labelledby="interview-title">
        <div className="session-meta">
          <button className="text-button" type="button" onClick={onBack}>
            Back
          </button>
          <span>{session.session_id}</span>
        </div>

        <h1 id="interview-title">Hello, {greetingName}</h1>
        <p className="subtitle">
          I am here to understand your experience. What problem would you like to talk about today?
        </p>

        {assistantMessage && (
          <div className="assistant-followup" aria-live="polite">
            {assistantMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="problem-form">
          <label htmlFor="problem">Your Problem</label>
          <textarea
            id="problem"
            placeholder={
              assistantMessage
                ? "Answer the follow-up questions here..."
                : "Describe the problem in your own words..."
            }
            value={problem}
            onChange={(event) => setProblem(event.target.value)}
            rows="8"
          />
          <button className="start-button" type="submit" disabled={!problem.trim() || isSubmitting}>
            {isSubmitting ? "Saving..." : "Submit Problem"}
          </button>
        </form>

        <p className="status-text" aria-live="polite">
          {message}
        </p>

        <button
          className="explore-button"
          type="button"
          disabled={!isComplete || isSelectingDomains}
          onClick={handleExplore}
        >
          {isSelectingDomains ? "Loading Domains..." : "Let's Explore"}
        </button>
      </section>
    </main>
  );
}
