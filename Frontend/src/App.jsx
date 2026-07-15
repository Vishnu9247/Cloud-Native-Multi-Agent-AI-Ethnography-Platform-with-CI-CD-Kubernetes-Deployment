import { useEffect, useState } from "react";

import ChatPage from "./pages/ChatPage.jsx";
import ResultsPage from "./pages/ResultsPage.jsx";
import WelcomePage from "./pages/WelcomePage.jsx";
import {
  clearSessionState,
  readStoredChatState,
  readStoredResults,
  readStoredSession,
  storeChatState,
  storeResults,
  storeSession,
} from "./utils/session.js";

function routeFromPathname(pathname) {
  if (pathname === "/chat") {
    return "chat";
  }

  if (pathname === "/results") {
    return "results";
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
  const [chatState, setChatState] = useState(() => readStoredChatState());
  const [results, setResults] = useState(() => readStoredResults());

  useEffect(() => {
    function handlePopState() {
      setRoute(routeFromPathname(window.location.pathname));
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function goToChat(payload) {
    setSession(payload.session);
    setChatState(payload.state);
    setResults(null);
    storeSession(payload.session);
    storeChatState(payload.state);
    navigateTo("/chat", setRoute);
  }

  function updateChatState(nextState) {
    setChatState(nextState);
    storeChatState(nextState);
  }

  function goToResults(payload) {
    const nextSession = payload.session || session;
    const nextResults = {
      patterns: payload.patterns || payload.state?.patterns || [],
      recommendations: payload.recommendations || payload.state?.recommendations || [],
      state: payload.state,
    };

    setSession(nextSession);
    setChatState(payload.state);
    setResults(nextResults);
    storeSession(nextSession);
    storeChatState(payload.state);
    storeResults(nextResults);
    navigateTo("/results", setRoute);
  }

  function startNewSession() {
    clearSessionState();
    setSession(null);
    setChatState(null);
    setResults(null);
    navigateTo("/", setRoute);
  }

  if (route === "chat" && session && chatState) {
    return (
      <ChatPage
        session={session}
        chatState={chatState}
        onStateChange={updateChatState}
        onResults={goToResults}
        onStartNew={startNewSession}
      />
    );
  }

  if (route === "results" && session && results) {
    return <ResultsPage session={session} results={results} onStartNew={startNewSession} />;
  }

  return <WelcomePage onSessionReady={goToChat} />;
}
