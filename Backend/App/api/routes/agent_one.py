from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from App.llm_utils.problem_framing_agent import app

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ProblemFramingRequest(BaseModel):
    session_id: str
    name: str
    age: str
    problem_conversation: List[ChatMessage]
    summary: str = ""
    is_complete: bool = False


@router.post("/problem-framing")
def run_problem_framing_agent(request: ProblemFramingRequest):
    state = {
        "session_id": request.session_id,
        "name": request.name,
        "age": request.age,
        "problem_conversation": [
            message.model_dump() for message in request.problem_conversation
        ],
        "summary": request.summary,
        "is_complete": request.is_complete,
    }

    result = app.invoke(state)

    return result