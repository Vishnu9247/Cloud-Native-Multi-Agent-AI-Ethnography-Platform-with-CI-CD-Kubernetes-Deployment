from typing import List, Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from App.llm_utils.pattern_analysis_agent import app


router = APIRouter()


class PatternAnalysisRequest(BaseModel):
    session_id: str
    problem: str

    domains: Dict[str, List[str]]

    pattern_questions: List[str] = Field(default_factory=list)
    pattern_context: List[Any] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


@router.post("/pattern-analysis")
def run_pattern_analysis(request: PatternAnalysisRequest):

    state = {
        "session_id": request.session_id,
        "problem": request.problem,
        "domains": request.domains,

        "pattern_questions": request.pattern_questions,
        "pattern_context": request.pattern_context,
        "patterns": request.patterns,
        "recommendations": request.recommendations,
    }

    result = app.invoke(state)

    return result