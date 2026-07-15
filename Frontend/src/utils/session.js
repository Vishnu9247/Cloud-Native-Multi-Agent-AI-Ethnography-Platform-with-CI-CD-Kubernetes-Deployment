const SESSION_STORAGE_KEY = "ethnography-assistant-session";
const CHAT_STATE_STORAGE_KEY = "ethnography-assistant-chat-state";
const RESULTS_STORAGE_KEY = "ethnography-assistant-results";

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

export function readStoredChatState() {
  return readStoredValue(CHAT_STATE_STORAGE_KEY);
}

export function storeChatState(state) {
  storeValue(CHAT_STATE_STORAGE_KEY, state);
}

export function readStoredResults() {
  return readStoredValue(RESULTS_STORAGE_KEY);
}

export function storeResults(results) {
  storeValue(RESULTS_STORAGE_KEY, results);
}

export function clearSessionState() {
  window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
  window.sessionStorage.removeItem(CHAT_STATE_STORAGE_KEY);
  window.sessionStorage.removeItem(RESULTS_STORAGE_KEY);
}
