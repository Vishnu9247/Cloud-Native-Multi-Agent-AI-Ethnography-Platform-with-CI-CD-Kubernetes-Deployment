from __future__ import annotations

from pathlib import Path

from evals.ethno_evals.models import Persona


REQUIRED_COLUMNS = [
    "Name",
    "Problem",
    "Person Details",
    "Ethnographic Solution",
]


def load_personas(path: Path) -> list[Persona]:
    try:
        import pandas as pd
    except ImportError as error:
        raise RuntimeError(
            "pandas is required to read personas.xlsx. Install backend/eval "
            "dependencies with `cd Backend; uv sync` or install evals/requirements.txt."
        ) from error

    if not path.exists():
        raise FileNotFoundError(f"Persona workbook not found: {path}")

    frame = pd.read_excel(path)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            f"Persona workbook is missing required columns: {', '.join(missing)}"
        )

    personas: list[Persona] = []
    for zero_index, row in frame.iterrows():
        if row[REQUIRED_COLUMNS].isna().all():
            continue

        personas.append(
            Persona(
                row_number=zero_index + 2,
                name=_clean_cell(row["Name"]) or f"Persona {zero_index + 1}",
                problem=_clean_cell(row["Problem"]),
                person_details=_clean_cell(row["Person Details"]),
                expected_solution=_clean_cell(row["Ethnographic Solution"]),
            )
        )
    return personas


def select_personas(personas: list[Persona], row_number: int | None) -> list[Persona]:
    if row_number is None:
        return personas

    selected = [persona for persona in personas if persona.row_number == row_number]
    if not selected:
        available = ", ".join(str(persona.row_number) for persona in personas[:10])
        raise ValueError(
            f"No persona found for Excel row {row_number}. "
            f"First available rows: {available}"
        )
    return selected


def _clean_cell(value: object) -> str:
    import pandas as pd

    if pd.isna(value):
        return ""
    return str(value).strip()
