import { cloneDomainMap } from "./domains.js";
import { normalizeTextList } from "./text.js";

export function buildPatternAnalysisRequest(session, resultsContext) {
  return {
    session_id: session.session_id,
    problem: resultsContext.problem,
    domains: cloneDomainMap(resultsContext.domains),
    pattern_questions: [],
    pattern_context: [],
    patterns: [],
    recommendations: [],
  };
}

export function normalizeResultsPayload(result, resultsContext) {
  return {
    raw: result,
    patterns: normalizeTextList(result?.patterns),
    recommendations: normalizeTextList(result?.recommendations),
    problem: resultsContext.problem,
    domains: cloneDomainMap(resultsContext.domains),
  };
}
