from typing import List, Dict
from fastapi import APIRouter
from pydantic import BaseModel, Field

from App.llm_utils.domain_interview_agent import (
    app,
    validate_user_answers
)
from App.database_utils.data_loader import insert_problem_conversation


router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class StartInterviewRequest(BaseModel):
    session_id: str
    problem: str

    domains_to_explore: Dict[str, List[str]]

    domains_explored: Dict[str, List[str]] = Field(
        default_factory=dict
    )


class ValidateAnswersRequest(BaseModel):
    session_id: str
    problem: str

    domains_to_explore: Dict[str, List[str]]
    domains_explored: Dict[str, List[str]]

    current_domain: str
    current_subdomain: str
    current_questions: List[str]

    conversations: List[ChatMessage]

    summaries: Dict[str, str] = Field(
        default_factory=dict
    )


@router.post("/start-domain-interview")
def start_domain_interview(request: StartInterviewRequest):

    state = {
        "session_id": request.session_id,
        "problem": request.problem,

        "domains_to_explore": request.domains_to_explore,
        "domains_explored": request.domains_explored,

        "current_domain": "",
        "current_subdomain": "",
        "current_questions": [],

        "conversations": [],

        "is_complete": False,
        "followup_message": "",
        "summary": "",
        "summaries": {}
    }

    result = app.invoke(state)

    return result


@router.post("/validate-domain-answer")
def validate_domain_answer(request: ValidateAnswersRequest):
    conversations = [
        message.model_dump()
        for message in request.conversations
    ]

    state = {
        "session_id": request.session_id,
        "problem": request.problem,

        "domains_to_explore": request.domains_to_explore,
        "domains_explored": request.domains_explored,

        "current_domain": request.current_domain,
        "current_subdomain": request.current_subdomain,
        "current_questions": request.current_questions,

        "conversations": conversations,

        "is_complete": False,
        "followup_message": "",
        "summary": "",

        "summaries": request.summaries
    }

    result = validate_user_answers(state)

    latest_answer = next(
        (
            message["content"]
            for message in reversed(conversations)
            if message.get("role") == "user"
        ),
        "",
    )

    insert_problem_conversation({
        "session_id": request.session_id,
        "domain": request.current_domain,
        "subdomain": request.current_subdomain,
        "questions": request.current_questions,
        "answers": latest_answer,
    })

    return result
