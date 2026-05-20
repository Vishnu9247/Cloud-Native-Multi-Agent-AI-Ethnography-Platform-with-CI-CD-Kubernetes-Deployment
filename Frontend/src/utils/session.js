const SESSION_STORAGE_KEY = "ethnography-assistant-session";
const EXPLORATION_STORAGE_KEY = "ethnography-assistant-exploration";
const RESULTS_STORAGE_KEY = "ethnography-assistant-results";

export function makeSessionId(name) {
  const cleanName = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");

  return `${cleanName || "guest"}_${timestamp}`;
}

function readStoredValue(key) {
  try {
    const value = window.sessionStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

function storeValue(key, value) {
  window.sessionStorage.setItem(key, JSON.stringify(value));
}

export function readStoredSession() {
  return readStoredValue(SESSION_STORAGE_KEY);
}

export function storeSession(session) {
  storeValue(SESSION_STORAGE_KEY, session);
}

export function readStoredExploration() {
  return readStoredValue(EXPLORATION_STORAGE_KEY);
}

export function storeExploration(exploration) {
  storeValue(EXPLORATION_STORAGE_KEY, exploration);
}

export function readStoredResults() {
  return readStoredValue(RESULTS_STORAGE_KEY);
}

export function storeResults(results) {
  storeValue(RESULTS_STORAGE_KEY, results);
}

export function clearSessionState() {
  window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
  window.sessionStorage.removeItem(EXPLORATION_STORAGE_KEY);
  window.sessionStorage.removeItem(RESULTS_STORAGE_KEY);
}
