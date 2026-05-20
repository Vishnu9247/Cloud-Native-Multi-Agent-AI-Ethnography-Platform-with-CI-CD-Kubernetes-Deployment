import { useEffect, useMemo, useState } from "react";

import {
  postPatternAnalysis,
  postStartDomainInterview,
  postValidateDomainAnswer,
} from "../api/client.js";
import DomainTimeline from "../components/DomainTimeline.jsx";
import {
  applyExploredState,
  cloneDomainMap,
  extractRawDomains,
  normalizeDomains,
} from "../utils/domains.js";
import { storeResults } from "../utils/session.js";
import { isCompletionMessage, normalizeTextList } from "../utils/text.js";

export default function ExplorePage({ session, exploration, onBack, onResults }) {
  const [interviewState, setInterviewState] = useState(null);
  const [answer, setAnswer] = useState("");
  const [isLoadingInterview, setIsLoadingInterview] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isGeneratingResults, setIsGeneratingResults] = useState(false);
  const [interviewMessage, setInterviewMessage] = useState("");
  const problem = exploration?.problem || exploration?.summary || "";
  const rawDomains = useMemo(() => {
    return exploration?.rawDomains || extractRawDomains(exploration?.raw);
  }, [exploration]);
  const domains = applyExploredState(
    exploration?.domains?.length ? exploration.domains : normalizeDomains(rawDomains),
    interviewState?.domains_explored || {},
  );
  const timelineItems = domains.flatMap((domain) => [
    {
      id: `domain-${domain.name}`,
      label: domain.name,
      type: "domain",
      isComplete: domain.isComplete,
    },
    ...domain.subdomains.map((subdomain) => ({
      id: `subdomain-${domain.name}-${subdomain.name}`,
      label: subdomain.name,
      type: "subdomain",
      isComplete: subdomain.isComplete,
    })),
  ]);
  const isAllComplete = Boolean(interviewState?.is_complete && !interviewState?.current_domain);

  useEffect(() => {
    if (!session || !problem || !rawDomains || Object.keys(rawDomains).length === 0 || interviewState) {
      return;
    }

    startInterview({
      domains_to_explore: cloneDomainMap(rawDomains),
      domains_explored: {},
      summaries: {},
    });
  }, [session, problem, rawDomains, interviewState]);

  async function startInterview(nextState) {
    setIsLoadingInterview(true);
    setInterviewMessage("Preparing questions...");

    try {
      const result = await postStartDomainInterview({
        session_id: session.session_id,
        problem,
        domains_to_explore: cloneDomainMap(nextState.domains_to_explore),
        domains_explored: cloneDomainMap(nextState.domains_explored),
      });
      setInterviewState({
        ...result,
        summaries: nextState.summaries || result.summaries || {},
      });
      setAnswer("");
      setInterviewMessage(result?.is_complete ? "All domains are complete." : "");
    } catch {
      setInterviewMessage("The backend could not start the domain interview.");
    } finally {
      setIsLoadingInterview(false);
    }
  }

  async function handleValidateAnswer(event) {
    event.preventDefault();

    if (!answer.trim() || !interviewState || isValidating) {
      return;
    }

    const existingConversations = interviewState.conversations || [];
    const seededConversations =
      existingConversations.length > 0
        ? existingConversations
        : [
            {
              role: "assistant",
              content: (interviewState.current_questions || []).join("\n"),
            },
          ];
    const nextConversations = [
      ...seededConversations,
      {
        role: "user",
        content: answer.trim(),
      },
    ];

    setIsValidating(true);
    setInterviewMessage("Validating your answer...");

    try {
      const result = await postValidateDomainAnswer({
        session_id: session.session_id,
        problem,
        domains_to_explore: cloneDomainMap(interviewState.domains_to_explore),
        domains_explored: cloneDomainMap(interviewState.domains_explored),
        current_domain: interviewState.current_domain,
        current_subdomain: interviewState.current_subdomain,
        current_questions: interviewState.current_questions || [],
        conversations: nextConversations,
        summaries: interviewState.summaries || {},
      });
      const normalizedResult = isCompletionMessage(result?.followup_message)
        ? {
            ...result,
            is_complete: true,
            followup_message: "",
          }
        : result;

      setAnswer("");

      if (normalizedResult?.is_complete && Object.keys(normalizedResult.domains_to_explore || {}).length > 0) {
        setInterviewState(normalizedResult);
        setInterviewMessage("Subdomain complete. Loading the next one...");
        await startInterview(normalizedResult);
        return;
      }

      setInterviewState(normalizedResult);
      setInterviewMessage(
        normalizedResult?.is_complete
          ? "All domains and subdomains are complete."
          : "Please answer the follow-up questions.",
      );
    } catch {
      setInterviewMessage("The backend could not validate this answer yet.");
    } finally {
      setIsValidating(false);
    }
  }

  async function handleGenerateResults() {
    if (!isAllComplete || isGeneratingResults) {
      return;
    }

    setIsGeneratingResults(true);
    setInterviewMessage("Generating patterns and recommendations...");

    try {
      const result = await postPatternAnalysis({
        session_id: session.session_id,
        problem,
        domains: cloneDomainMap(rawDomains),
        pattern_questions: [],
        pattern_context: [],
        patterns: [],
        recommendations: [],
      });
      const nextResults = {
        raw: result,
        patterns: normalizeTextList(result?.patterns),
        recommendations: normalizeTextList(result?.recommendations),
        problem,
      };

      storeResults(nextResults);
      onResults(nextResults);
    } catch {
      setInterviewMessage("The backend could not generate results yet.");
    } finally {
      setIsGeneratingResults(false);
    }
  }

  return (
    <main className="explore-shell">
      <aside className="domain-sidebar" aria-labelledby="domains-title">
        <button className="text-button" type="button" onClick={onBack}>
          Back
        </button>
        <h1 id="domains-title">Explore</h1>
        <p className="sidebar-subtitle">{session?.session_id}</p>

        <DomainTimeline items={timelineItems} />
      </aside>

      <section className="explore-content" aria-labelledby="questionnaire-title">
        <div className="questionnaire-header">
          <span>{interviewState?.current_domain || "Domain Interview"}</span>
          <h2 id="questionnaire-title">
            {interviewState?.current_subdomain || (isAllComplete ? "Completed" : "Preparing")}
          </h2>
        </div>

        {isLoadingInterview ? (
          <p className="interview-status">Preparing questions...</p>
        ) : isAllComplete ? (
          <div className="completion-panel">
            <h3>Interview Complete</h3>
            <p>All domains and subdomains are complete. You can now generate your results.</p>
            <button
              className="primary-action"
              type="button"
              onClick={handleGenerateResults}
              disabled={isGeneratingResults}
            >
              {isGeneratingResults ? "Generating..." : "Generate Results"}
            </button>
          </div>
        ) : interviewState?.current_questions?.length ? (
          <>
            <div className="question-workspace">
              <div className="question-list">
                {interviewState.current_questions.map((question, index) => (
                  <p key={`${interviewState.current_subdomain}-${index}`}>
                    <strong>{index + 1}.</strong> {question}
                  </p>
                ))}
              </div>

              <form className="answer-form" onSubmit={handleValidateAnswer}>
                <label htmlFor="domain-answer">Your Answer</label>
                <textarea
                  id="domain-answer"
                  placeholder="Share your answer in as much detail as you can..."
                  value={answer}
                  onChange={(event) => setAnswer(event.target.value)}
                  rows="13"
                />
                <button className="start-button" type="submit" disabled={!answer.trim() || isValidating}>
                  {isValidating ? "Checking..." : "Submit Answer"}
                </button>
              </form>
            </div>

            {interviewState.followup_message && (
              <div className="assistant-followup followup-wide">{interviewState.followup_message}</div>
            )}
          </>
        ) : (
          <p className="interview-status">No questions are available yet.</p>
        )}

        <p className="status-text" aria-live="polite">
          {interviewMessage}
        </p>
      </section>
    </main>
  );
}
