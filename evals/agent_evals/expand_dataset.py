from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any


HERE = Path(__file__).parent
SEED_PATH = HERE / "dataset" / "agent_eval_dataset.json"
OUTPUT_PATH = HERE / "dataset" / "agent_eval_dataset_40.json"

STYLES = [
    ("direct", "", ""),
    ("concise", "To put it simply, ", ""),
    ("emotional", "This is hard to admit, but ", ""),
    ("reflective", "I've been trying to make sense of this: ", " That's what keeps standing out to me."),
    ("conversational", "So, basically, ", " I hope that makes sense."),
]

NAMES = [
    ["Maya", "Nora", "Iris", "Talia", "Renee"],
    ["Jon", "Marcus", "Evan", "Caleb", "Owen"],
    ["Elena", "Sofia", "Lucia", "Camila", "Marisol"],
    ["Darius", "Walter", "Samuel", "Arthur", "Henry"],
    ["Priya", "Meera", "Anika", "Leena", "Kavya"],
    ["Noah", "Miles", "Adrian", "Felix", "Theo"],
    ["Amina", "Zara", "Layla", "Nadia", "Samira"],
    ["Leo", "Julian", "Mateo", "Andre", "Simon"],
]


def styled(text: str, style_index: int) -> str:
    if not text or style_index == 0:
        return text
    _, prefix, suffix = STYLES[style_index]
    first = text[0].lower() + text[1:] if text else text
    return f"{prefix}{first}{suffix}".strip()


def style_user_messages(messages: list[dict[str, str]], style_index: int) -> None:
    if style_index == 0:
        return
    for message in messages:
        if message.get("role") == "user":
            message["content"] = styled(str(message.get("content", "")), style_index)


def expand(seed_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(seed_cases) != 8:
        raise ValueError(f"Expected 8 carefully authored seed cases, found {len(seed_cases)}.")
    expanded: list[dict[str, Any]] = []
    for seed_index, seed in enumerate(seed_cases):
        for style_index, (style_name, _, _) in enumerate(STYLES):
            case = copy.deepcopy(seed)
            ordinal = seed_index * len(STYLES) + style_index + 1
            case["case_id"] = f"ETHNO-{ordinal:03d}"
            case["source_case_id"] = seed["case_id"]
            case["dataset_style"] = style_name
            case["split"] = "development" if style_index < 3 else ("validation" if style_index == 3 else "test")
            case["persona"]["name"] = NAMES[seed_index][style_index]
            case["persona"]["age"] = max(18, int(seed["persona"]["age"]) + style_index - 2)
            case["legacy_evaluator_fields"]["Name"] = case["persona"]["name"]
            case["legacy_evaluator_fields"]["Person Details"] = re.sub(
                r"^\d+-year-old",
                f"{case['persona']['age']}-year-old",
                case["legacy_evaluator_fields"]["Person Details"],
            )
            case["initial_problem"] = styled(seed["initial_problem"], style_index)
            case["problem_framing"]["clarification_answer"] = styled(
                seed["problem_framing"].get("clarification_answer", ""), style_index
            )
            for rephrase in case["domain_interview"]["rephrase_cases"]:
                rephrase["context"] = styled(rephrase["context"], style_index)
            for validation in case["interview_validation"]["validation_cases"]:
                style_user_messages(validation["conversation"], style_index)
            style_user_messages(case["interview_validation"]["summary_conversation"], style_index)
            expanded.append(case)
    return expanded


def validate(cases: list[dict[str, Any]]) -> None:
    agents = (
        "problem_framing",
        "domain_selection",
        "domain_interview",
        "interview_validation",
        "pattern_analysis",
    )
    if len(cases) != 40:
        raise ValueError(f"Expected exactly 40 cases, found {len(cases)}.")
    if len({case["case_id"] for case in cases}) != 40:
        raise ValueError("Case IDs are not unique.")
    if len({case["persona"]["name"] for case in cases}) != 40:
        raise ValueError("Persona names are not unique.")
    for case in cases:
        missing = [agent for agent in agents if agent not in case]
        if missing:
            raise ValueError(f"{case['case_id']} is missing agent sections: {missing}")
        pattern = case["pattern_analysis"]
        for supported in pattern["supported_patterns"]:
            if len(supported["evidence_ids"]) < 2:
                raise ValueError(f"{case['case_id']} contains a pattern with fewer than two evidence items.")


def main() -> None:
    seed_cases = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    cases = expand(seed_cases)
    validate(cases)
    OUTPUT_PATH.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {OUTPUT_PATH}")
    for agent in ("problem_framing", "domain_selection", "domain_interview", "interview_validation", "pattern_analysis"):
        print(f"{agent}: {sum(1 for case in cases if agent in case)} cases")


if __name__ == "__main__":
    main()
