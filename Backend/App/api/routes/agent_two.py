from typing import List, Dict
from fastapi import APIRouter
from pydantic import BaseModel, Field

from App.llm_utils.domain_selection_agent import app

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class DomainSelectionRequest(BaseModel):
    session_id: str
    problem: str
    domains: Dict[str, List[str]] = Field(default_factory=dict)


@router.post("/domain-selection")
def run_domain_selection_agent(request: DomainSelectionRequest):
    state = {
        "session_id": request.session_id,
        "problem": request.problem,
        "domains": request.domains,
   }

    result = app.invoke(state)

    return result
