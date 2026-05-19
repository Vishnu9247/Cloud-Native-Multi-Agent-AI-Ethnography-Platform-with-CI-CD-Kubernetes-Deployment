import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
const SESSION_STORAGE_KEY = "ethnography-assistant-session";
const EXPLORATION_STORAGE_KEY = "ethnography-assistant-exploration";
const RESULTS_STORAGE_KEY = "ethnography-assistant-results";

function makeSessionId(name) {
  const cleanName = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");

  return `${cleanName || "guest"}_${timestamp}`;
}

async function postJson(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

async function postProblemFraming(body) {
  try {
    return await postJson("/agent/problem-framing", body);
  } catch (error) {
    return postJson("/problem-framing", body);
  }
}

async function postDomainSelection(body) {
  return postJson("/agent/domain-selection", body);
}

async function postStartDomainInterview(body) {
  return postJson("/agent/start-domain-interview", body);
}

async function postValidateDomainAnswer(body) {
  return postJson("/agent/validate-domain-answer", body);
}

async function postPatternAnalysis(body) {
  return postJson("/agent/pattern-analysis", body);
}

async function postDeleteCollection(body) {
  return postJson("/vector/delete_collection", body);
}

function readStoredSession() {
  try {
    const value = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

function storeSession(session) {
  window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

function readStoredExploration() {
  try {
    const value = window.sessionStorage.getItem(EXPLORATION_STORAGE_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

function storeExploration(exploration) {
  window.sessionStorage.setItem(EXPLORATION_STORAGE_KEY, JSON.stringify(exploration));
}

function readStoredResults() {
  try {
    const value = window.sessionStorage.getItem(RESULTS_STORAGE_KEY);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

function storeResults(results) {
  window.sessionStorage.setItem(RESULTS_STORAGE_KEY, JSON.stringify(results));
}

function clearSessionState() {
  window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
  window.sessionStorage.removeItem(EXPLORATION_STORAGE_KEY);
  window.sessionStorage.removeItem(RESULTS_STORAGE_KEY);
}

function cloneDomainMap(domains) {
  return Object.fromEntries(
    Object.entries(domains || {}).map(([domain, subdomains]) => [
      domain,
      Array.isArray(subdomains) ? [...subdomains] : [],
    ]),
  );
}

function getLatestAssistantMessage(conversation) {
  const message = [...conversation].reverse().find((item) => item.role === "assistant")?.content || "";
  return isCompletionMessage(message) ? "" : message;
}

function normalizeDomains(rawDomains, exploredDomains = {}) {
  if (!rawDomains) {
    return [];
  }

  if (Array.isArray(rawDomains)) {
    return rawDomains.map((domain) => {
      const domainName = domain.domain || domain.name || domain.title || "Untitled Domain";
      const subdomains = domain.subdomains || domain.sub_domains || domain.children || [];

      return {
        name: domainName,
        isComplete: Boolean(domain.is_complete || domain.completed),
        subdomains: normalizeSubdomains(domainName, subdomains, exploredDomains),
      };
    });
  }

  return Object.entries(rawDomains).map(([domainName, subdomains]) => ({
    name: domainName,
    isComplete:
      Array.isArray(exploredDomains[domainName]) &&
      Array.isArray(subdomains) &&
      subdomains.length > 0 &&
      exploredDomains[domainName].length >= subdomains.length,
    subdomains: normalizeSubdomains(domainName, subdomains, exploredDomains),
  }));
}

function normalizeSubdomains(domainName, subdomains, exploredDomains) {
  if (!Array.isArray(subdomains)) {
    return [];
  }

  return subdomains.map((subdomain) => {
    const name =
      typeof subdomain === "string"
        ? subdomain
        : subdomain.subdomain || subdomain.name || subdomain.title || "Untitled Subdomain";
    const exploredSubdomains = exploredDomains?.[domainName] || [];

    return {
      name,
      isComplete:
        Boolean(typeof subdomain === "object" && (subdomain.is_complete || subdomain.completed)) ||
        exploredSubdomains.includes(name),
    };
  });
}

function extractDomainsFromAgentState(agentState) {
  const rawDomains =
    agentState?.domains_to_explore ||
    agentState?.domainsToExplore ||
    agentState?.domains ||
    agentState?.domain_subdomains ||
    agentState?.domain_map ||
    agentState?.data?.domains_to_explore ||
    agentState?.data?.domainsToExplore ||
    agentState?.data?.domains ||
    {};

  const exploredDomains = agentState?.domains_explored || agentState?.completed_domains || {};

  return normalizeDomains(rawDomains, exploredDomains);
}

function extractRawDomains(agentState) {
  return cloneDomainMap(
    agentState?.domains ||
      agentState?.domains_to_explore ||
      agentState?.data?.domains ||
      agentState?.data?.domains_to_explore ||
      {},
  );
}

function applyExploredState(domains, exploredDomains = {}) {
  return domains.map((domain) => {
    const exploredSubdomains = exploredDomains[domain.name] || [];
    const subdomains = domain.subdomains.map((subdomain) => ({
      ...subdomain,
      isComplete: exploredSubdomains.includes(subdomain.name),
    }));

    return {
      ...domain,
      subdomains,
      isComplete: subdomains.length > 0 && subdomains.every((subdomain) => subdomain.isComplete),
    };
  });
}

function isCompletionMessage(message) {
  return typeof message === "string" && message.trim().toLowerCase().replace(/[.!]+$/g, "") === "complete";
}

function normalizeTextList(value) {
  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).filter(Boolean);
  }

  if (typeof value === "string" && value.trim()) {
    return [value.trim()];
  }

  return [];
}

function WelcomePage({ onSessionReady }) {
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

function InterviewPage({ session, onBack, onExplore }) {
  const [problem, setProblem] = useState("");
  const [conversation, setConversation] = useState([]);
  const [agentState, setAgentState] = useState(null);
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
    } catch (error) {
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
    } catch (error) {
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

function ExplorePage({ session, exploration, onBack, onResults }) {
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
    } catch (error) {
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
    } catch (error) {
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
    } catch (error) {
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

        {timelineItems.length > 0 ? (
          <ol className="domain-timeline">
            {timelineItems.map((item, index) => (
              <li
                className={`timeline-item ${item.type}${item.isComplete ? " is-complete" : ""}`}
                key={item.id}
              >
                <span
                  className={`timeline-rail${index === timelineItems.length - 1 ? " is-last" : ""}${
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
        ) : (
          <p className="empty-domains">No domains were returned yet.</p>
        )}
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
            <button className="primary-action" type="button" onClick={handleGenerateResults} disabled={isGeneratingResults}>
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

function ProgressDot({ isComplete }) {
  return <span className={`progress-dot${isComplete ? " is-complete" : ""}`} aria-hidden="true" />;
}

function ResultsPage({ session, results, onEndSession }) {
  const [isEnding, setIsEnding] = useState(false);
  const [message, setMessage] = useState("");
  const patterns = normalizeTextList(results?.patterns || results?.raw?.patterns);
  const recommendations = normalizeTextList(results?.recommendations || results?.raw?.recommendations);

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
    } catch (error) {
      setMessage("The backend could not delete the session collection yet.");
    } finally {
      setIsEnding(false);
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
        <button className="danger-button" type="button" onClick={handleEndSession} disabled={isEnding}>
          {isEnding ? "Ending..." : "End Session"}
        </button>
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

function EndPage({ onStartNew }) {
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

function App() {
  const [route, setRoute] = useState(() => {
    if (window.location.pathname === "/interview") {
      return "interview";
    }

    if (window.location.pathname === "/explore") {
      return "explore";
    }

    if (window.location.pathname === "/results") {
      return "results";
    }

    if (window.location.pathname === "/ended") {
      return "ended";
    }

    return "welcome";
  });
  const [session, setSession] = useState(() => readStoredSession());
  const [exploration, setExploration] = useState(() => readStoredExploration());
  const [results, setResults] = useState(() => readStoredResults());

  useEffect(() => {
    function handlePopState() {
      if (window.location.pathname === "/interview") {
        setRoute("interview");
      } else if (window.location.pathname === "/explore") {
        setRoute("explore");
      } else if (window.location.pathname === "/results") {
        setRoute("results");
      } else if (window.location.pathname === "/ended") {
        setRoute("ended");
      } else {
        setRoute("welcome");
      }
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function goToInterview(nextSession) {
    setSession(nextSession);
    storeSession(nextSession);
    window.history.pushState(null, "", "/interview");
    setRoute("interview");
  }

  function goToWelcome() {
    window.history.pushState(null, "", "/");
    setRoute("welcome");
  }

  function goToExplore(nextExploration) {
    setExploration(nextExploration);
    storeExploration(nextExploration);
    window.history.pushState(null, "", "/explore");
    setRoute("explore");
  }

  function goToResults(nextResults) {
    setResults(nextResults);
    storeResults(nextResults);
    window.history.pushState(null, "", "/results");
    setRoute("results");
  }

  function goBackToInterview() {
    window.history.pushState(null, "", "/interview");
    setRoute("interview");
  }

  function goToEnded() {
    setSession(null);
    setExploration(null);
    setResults(null);
    window.history.pushState(null, "", "/ended");
    setRoute("ended");
  }

  function startNewSession() {
    clearSessionState();
    setSession(null);
    setExploration(null);
    setResults(null);
    window.history.pushState(null, "", "/");
    setRoute("welcome");
  }

  if (route === "ended") {
    return <EndPage onStartNew={startNewSession} />;
  }

  if (route === "results" && session && results) {
    return <ResultsPage session={session} results={results} onEndSession={goToEnded} />;
  }

  if (route === "explore" && session) {
    return <ExplorePage session={session} exploration={exploration} onBack={goBackToInterview} onResults={goToResults} />;
  }

  if (route === "interview" && session) {
    return <InterviewPage session={session} onBack={goToWelcome} onExplore={goToExplore} />;
  }

  return <WelcomePage onSessionReady={goToInterview} />;
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
