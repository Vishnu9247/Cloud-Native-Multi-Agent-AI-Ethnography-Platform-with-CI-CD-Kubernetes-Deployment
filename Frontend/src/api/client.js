const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export async function postJson(path, body) {
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

export async function postProblemFraming(body) {
  try {
    return await postJson("/agent/problem-framing", body);
  } catch {
    return postJson("/problem-framing", body);
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
