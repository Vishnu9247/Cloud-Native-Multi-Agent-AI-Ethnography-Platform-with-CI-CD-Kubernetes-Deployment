export function isCompletionMessage(message) {
  return (
    typeof message === "string" &&
    message.trim().toLowerCase().replace(/[.!]+$/g, "") === "complete"
  );
}

export function getLatestAssistantMessage(conversation) {
  const message =
    [...conversation].reverse().find((item) => item.role === "assistant")?.content || "";
  return isCompletionMessage(message) ? "" : message;
}

export function normalizeTextList(value) {
  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).filter(Boolean);
  }

  if (typeof value === "string" && value.trim()) {
    return [value.trim()];
  }

  return [];
}
