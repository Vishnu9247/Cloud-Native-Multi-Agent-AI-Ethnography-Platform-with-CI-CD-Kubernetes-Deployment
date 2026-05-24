const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 240000);

function formatErrorMessage(path, status, responseText) {
  if (!responseText) {
    return `${path} failed with status ${status}`;
  }

  try {
    const parsed = JSON.parse(responseText);
    const detail = parsed.detail || parsed.message || parsed.error;

    if (typeof detail === "string") {
      return `${path} failed with status ${status}: ${detail}`;
    }

    if (Array.isArray(detail)) {
      return `${path} failed with status ${status}: ${detail
        .map((item) => item.msg || item.message || JSON.stringify(item))
        .join("; ")}`;
    }

    return `${path} failed with status ${status}: ${JSON.stringify(parsed)}`;
  } catch {
    return `${path} failed with status ${status}: ${responseText}`;
  }
}

export async function postJson(path, body, options = {}) {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!response.ok) {
      const message = await response.text();
      const error = new Error(formatErrorMessage(path, response.status, message));
      error.status = response.status;
      error.responseText = message;
      throw error;
    }

    const text = await response.text();
    return text ? JSON.parse(text) : null;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function postProblemFraming(body) {
  try {
    return await postJson("/agent/problem-framing", body);
  } catch (error) {
    if (error?.status === 404) {
      return postJson("/problem-framing", body);
    }

    throw error;
  }
}

export function postDomainSelection(body) {
  return postJson("/agent/domain-selection", body);
}

export function postStartDomainInterview(body) {
  return postJson("/agent/start-domain-interview", body);
}

export function postValidateDomainAnswer(body) {
  return postJson("/agent/validate-domain-answer", body);
}

export function postPatternAnalysis(body) {
  return postJson("/agent/pattern-analysis", body);
}

export function postDeleteCollection(body) {
  return postJson("/vector/delete_collection", body);
}

export function postAddProblem(body) {
  return postJson("/vector/add_problem", body);
}

export function postSessionDetails(body) {
  return postJson("/database/add-session-details", body);
}
