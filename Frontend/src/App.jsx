import { useEffect, useState } from "react";

import EndPage from "./pages/EndPage.jsx";
import ExplorePage from "./pages/ExplorePage.jsx";
import InterviewPage from "./pages/InterviewPage.jsx";
import ResultsPage from "./pages/ResultsPage.jsx";
import WelcomePage from "./pages/WelcomePage.jsx";
import {
  clearSessionState,
  readStoredExploration,
  readStoredResults,
  readStoredSession,
  storeExploration,
  storeResults,
  storeSession,
} from "./utils/session.js";

function routeFromPathname(pathname) {
  if (pathname === "/interview") {
    return "interview";
  }

  if (pathname === "/explore") {
    return "explore";
  }

  if (pathname === "/results") {
    return "results";
  }

  if (pathname === "/ended") {
    return "ended";
  }

  return "welcome";
}

function navigateTo(path, setRoute) {
  window.history.pushState(null, "", path);
  setRoute(routeFromPathname(path));
}

export default function App() {
  const [route, setRoute] = useState(() => routeFromPathname(window.location.pathname));
  const [session, setSession] = useState(() => readStoredSession());
  const [exploration, setExploration] = useState(() => readStoredExploration());
  const [results, setResults] = useState(() => readStoredResults());

  useEffect(() => {
    function handlePopState() {
      setRoute(routeFromPathname(window.location.pathname));
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function goToInterview(nextSession) {
    setSession(nextSession);
    storeSession(nextSession);
    navigateTo("/interview", setRoute);
  }

  function goToWelcome() {
    navigateTo("/", setRoute);
  }

  function goToExplore(nextExploration) {
    setExploration(nextExploration);
    storeExploration(nextExploration);
    navigateTo("/explore", setRoute);
  }

  function goToResults(nextResults) {
    setResults(nextResults);
    storeResults(nextResults);
    navigateTo("/results", setRoute);
  }

  function updateResults(nextResults) {
    setResults(nextResults);
    storeResults(nextResults);
  }

  function goBackToInterview() {
    navigateTo("/interview", setRoute);
  }

  function goToEnded() {
    setSession(null);
    setExploration(null);
    setResults(null);
    navigateTo("/ended", setRoute);
  }

  function startNewSession() {
    clearSessionState();
    setSession(null);
    setExploration(null);
    setResults(null);
    navigateTo("/", setRoute);
  }

  if (route === "ended") {
    return <EndPage onStartNew={startNewSession} />;
  }

  if (route === "results" && session && results) {
    return (
      <ResultsPage
        session={session}
        results={results}
        onEndSession={goToEnded}
        onResultsUpdate={updateResults}
      />
    );
  }

  if (route === "explore" && session) {
    return (
      <ExplorePage
        session={session}
        exploration={exploration}
        onBack={goBackToInterview}
        onResults={goToResults}
      />
    );
  }

  if (route === "interview" && session) {
    return <InterviewPage session={session} onBack={goToWelcome} onExplore={goToExplore} />;
  }

  return <WelcomePage onSessionReady={goToInterview} />;
}
