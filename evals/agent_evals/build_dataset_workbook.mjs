import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const sourcePath = process.argv[2] ?? "evals/agent_evals/dataset/agent_eval_dataset_40.json";
const outputPath = process.argv[3] ?? "evals/agent_evals/dataset/agent_eval_dataset.xlsx";
const previewDir = process.argv[4] ?? "evals/agent_evals/dataset/.previews";
const cases = JSON.parse(await fs.readFile(sourcePath, "utf8"));

const workbook = Workbook.create();
const colors = {
  navy: "#17324D",
  teal: "#147D80",
  pale: "#E8F3F3",
  light: "#F4F7FA",
  white: "#FFFFFF",
  gray: "#52606D",
};

function json(value) {
  return JSON.stringify(value, null, 2);
}

function addSheet(name, headers, rows, widths) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const matrix = [headers, ...rows];
  const range = sheet.getRangeByIndexes(0, 0, matrix.length, headers.length);
  range.values = matrix;
  range.format = {
    font: { name: "Aptos", size: 10, color: "#1F2933" },
    verticalAlignment: "top",
  };
  range.format.wrapText = true;
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format = {
    fill: colors.navy,
    font: { name: "Aptos Display", size: 11, bold: true, color: colors.white },
    verticalAlignment: "center",
  };
  sheet.getRangeByIndexes(0, 0, matrix.length, headers.length).format.borders = {
    insideHorizontal: { style: "thin", color: "#D9E2EC" },
    bottom: { style: "thin", color: "#BCCCDC" },
  };
  sheet.getRangeByIndexes(1, 0, Math.max(rows.length, 1), 1).format = {
    fill: colors.pale,
    font: { bold: true, color: colors.teal },
  };
  widths.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, matrix.length, 1).format.columnWidth = width;
  });
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format.rowHeight = 28;
  sheet.getRangeByIndexes(1, 0, Math.max(rows.length, 1), headers.length).format.rowHeight = 84;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);
  sheet.tables.add(
    sheet.getRangeByIndexes(0, 0, matrix.length, headers.length),
    true,
    `${name.replace(/[^A-Za-z0-9]/g, "")}Table`,
  );
  return sheet;
}

const guide = workbook.worksheets.add("Guide");
guide.showGridLines = false;
guide.getRange("A1:F1").merge();
guide.getRange("A1").values = [["Ethnography Agent Prompt Evaluation Dataset"]];
guide.getRange("A1:F1").format = {
  fill: colors.navy,
  font: { name: "Aptos Display", size: 18, bold: true, color: colors.white },
  verticalAlignment: "center",
};
guide.getRange("A1:F1").format.rowHeight = 38;
guide.getRange("A3:B15").values = [
  ["Purpose", "Grounded A/B/C evaluation of Tight, Few-shot, and Checklist prompts for five independent agents."],
  ["Cases per agent", cases.length],
  ["Total agent-case combinations", cases.length * 5],
  ["Development", cases.filter((item) => item.split === "development").length],
  ["Validation", cases.filter((item) => item.split === "validation").length],
  ["Test", cases.filter((item) => item.split === "test").length],
  ["Prompt variants", "A / Tight, B / Few-shot, C / Checklist"],
  ["Model", "Ollama llama3.2, temperature 0, seed 42; LLM used as judge"],
  ["Metric range", "All quality metrics are normalized to 0.0-1.0"],
  ["Grounding", "Expected outputs derive only from each persona fact ledger and evidence records."],
  ["Pattern rule", "A supported pattern requires at least two evidence items; isolated observations are not patterns."],
  ["Logs", "Each evaluator writes calls.jsonl and run.log with complete agent/judge prompts and responses."],
  ["Outputs", "Each evaluator writes detailed CSV rows and a compact JSON summary by variant."],
];
guide.getRange("A3:A15").format = { fill: colors.pale, font: { bold: true, color: colors.teal } };
guide.getRange("A3:B15").format.wrapText = true;
guide.getRange("A3:B15").format.borders = { preset: "inside", style: "thin", color: "#D9E2EC" };
guide.getRange("A:A").format.columnWidth = 22;
guide.getRange("B:B").format.columnWidth = 78;
guide.getRange("A3:B15").format.rowHeight = 42;

addSheet(
  "Personas",
  ["Case ID", "Source Case", "Style", "Split", "Difficulty", "Family", "Name", "Age", "Role", "Context", "Constraints", "Fact Ledger", "Initial Problem", "Expected Solution"],
  cases.map((item) => [
    item.case_id, item.source_case_id, item.dataset_style, item.split, item.difficulty, item.problem_family, item.persona.name,
    item.persona.age, item.persona.role, item.persona.context, json(item.persona.constraints),
    json(item.persona.fact_ledger), item.initial_problem, item.legacy_evaluator_fields["Ethnographic Solution"],
  ]),
  [15, 15, 16, 13, 13, 23, 15, 8, 24, 38, 34, 52, 58, 58],
);

addSheet(
  "Problem Framing",
  ["Case ID", "Initial Complete", "Missing Dimension", "Acceptable Follow-up", "Clarification Answer", "Summary Key Phrases", "Forbidden Inferences"],
  cases.map((item) => [item.case_id, item.problem_framing.initial_complete, item.problem_framing.missing_dimension,
    item.problem_framing.acceptable_followup, item.problem_framing.clarification_answer,
    json(item.problem_framing.summary_key_phrases), json(item.problem_framing.forbidden_inferences)]),
  [15, 18, 20, 50, 58, 45, 45],
);

addSheet(
  "Domain Selection",
  ["Case ID", "Required", "Acceptable Optional", "Irrelevant", "Priority Order"],
  cases.map((item) => [item.case_id, json(item.domain_selection.required), json(item.domain_selection.acceptable_optional),
    json(item.domain_selection.irrelevant), json(item.domain_selection.priority_order)]),
  [15, 55, 48, 45, 38],
);

addSheet(
  "Domain Interview",
  ["Case ID", "Domain", "Subdomain", "Target Cues", "Rephrase Cases"],
  cases.map((item) => [item.case_id, item.domain_interview.domain, item.domain_interview.subdomain,
    json(item.domain_interview.target_cues), json(item.domain_interview.rephrase_cases)]),
  [15, 20, 22, 45, 95],
);

addSheet(
  "Validation",
  ["Case ID", "Domain", "Subdomain", "Validation Cases", "Summary Conversation", "Summary Key Phrases", "Forbidden Claims"],
  cases.map((item) => [item.case_id, item.interview_validation.domain, item.interview_validation.subdomain,
    json(item.interview_validation.validation_cases), json(item.interview_validation.summary_conversation),
    json(item.interview_validation.summary_key_phrases), json(item.interview_validation.forbidden_claims)]),
  [15, 20, 22, 85, 95, 48, 45],
);

addSheet(
  "Pattern Analysis",
  ["Case ID", "Question Target Cues", "Evidence Context", "Expect Empty", "Supported Patterns", "Forbidden Patterns", "Recommendation Cues", "Constraints"],
  cases.map((item) => [item.case_id, json(item.pattern_analysis.question_target_cues), json(item.pattern_analysis.context),
    item.pattern_analysis.expect_empty_patterns, json(item.pattern_analysis.supported_patterns),
    json(item.pattern_analysis.forbidden_patterns), json(item.pattern_analysis.recommendation_cues), json(item.pattern_analysis.constraints)]),
  [15, 45, 95, 16, 80, 50, 48, 40],
);

addSheet(
  "Legacy Personas",
  ["Name", "Problem", "Person Details", "Ethnographic Solution"],
  cases.map((item) => [item.legacy_evaluator_fields.Name, item.legacy_evaluator_fields.Problem,
    item.legacy_evaluator_fields["Person Details"], item.legacy_evaluator_fields["Ethnographic Solution"]]),
  [18, 58, 65, 70],
);

addSheet(
  "Metric Definitions",
  ["Metric", "Range", "Source", "Definition"],
  [
    ["metric_overall_score", "0.0-1.0", "Combined", "Weighted combination of format validity, deterministic task checks, judge overall, groundedness, and judge confidence."],
    ["metric_groundedness", "0.0-1.0", "LLM judge", "Degree to which every material output claim is supported by the case reference evidence."],
    ["metric_relevance", "0.0-1.0", "LLM judge", "Alignment of the response with the requested domain, subdomain, task, and user problem."],
    ["metric_completeness", "0.0-1.0", "LLM judge", "Coverage of the required information without demanding irrelevant detail."],
    ["metric_faithfulness", "0.0-1.0", "LLM judge", "Accuracy to the provided conversation and oracle, with no distortion or unsupported inference."],
    ["metric_coherence", "0.0-1.0", "LLM judge", "Clarity, internal consistency, and readability of the output."],
    ["metric_instruction_compliance", "0.0-1.0", "LLM judge", "Compliance with the prompt's output schema, constraints, and role boundaries."],
    ["metric_safety", "0.0-1.0", "LLM judge", "Absence of diagnosis, judgment, unsafe advice, or constraint-conflicting recommendations."],
    ["metric_confidence", "0.0-1.0", "LLM judge", "Judge confidence in its evaluation based on the clarity and sufficiency of the reference evidence."],
    ["metric_format_valid", "0.0-1.0", "Deterministic", "Whether the response obeys the required JSON, exact-token, single-question, or section format."],
    ["metric_precision / recall / f1", "0.0-1.0", "Deterministic", "Exact normalized domain/subdomain selection agreement with required gold labels."],
    ["metric_empty_decision_accuracy", "0.0-1.0", "Deterministic", "Whether pattern analysis correctly returns no patterns when evidence is insufficient."],
  ],
  [34, 14, 22, 100],
);

addSheet(
  "Log Schema",
  ["Field", "Example", "Description"],
  [
    ["run_id", "20260715T120000Z-ab12cd34", "Unique identifier shared by every call in one evaluator run."],
    ["timestamp_utc", "'2026-07-15T12:00:00+00:00", "UTC timestamp for the call."],
    ["agent / task / variant / case_id", "domain_selection / select / a / ETHNO-001", "Coordinates the call to an evaluator row."],
    ["call_type", "agent or judge", "Distinguishes evaluated-agent generation from LLM judge generation."],
    ["prompt", "Complete rendered prompt", "Exact user/system-style prompt sent to Ollama, including case context."],
    ["response", "Complete model response", "Untruncated response returned by Ollama."],
    ["elapsed_seconds", "12.45", "Wall-clock latency for the call."],
    ["prompt_tokens / output_tokens", "850 / 120", "Token counts reported by Ollama."],
    ["calls.jsonl", "Machine-readable", "One lossless JSON object per LLM call."],
    ["run.log", "Human-readable", "Prompt and response transcript separated into labeled call blocks."],
  ],
  [32, 44, 100],
);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const inspect = await workbook.inspect({
  kind: "sheet,table",
  maxChars: 5000,
  tableMaxRows: 3,
  tableMaxCols: 6,
});
console.log(inspect.ndjson);

for (const sheetName of ["Guide", "Personas", "Problem Framing", "Domain Selection", "Domain Interview", "Validation", "Pattern Analysis", "Legacy Personas", "Metric Definitions", "Log Schema"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 0.8, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(" ", "_")}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`Saved ${outputPath}`);
