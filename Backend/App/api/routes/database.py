from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from App.database_utils.data_loader import (
    insert_session_details,
    insert_problem_conversation,
    insert_session_results,
    get_session_results,
)


router = APIRouter()


class SessionDetails(BaseModel):
    session_id: str
    name: str
    age: int
    problem: str


class ProblemConversation(BaseModel):
    session_id: str
    domain: str
    subdomain: str
    questions: str
    answers: str

class SessionResults(BaseModel):
    session_id: str
    patterns: List[str]
    recommendations: List[str]


@router.post("/add-session-details")
def add_session_details(data: SessionDetails):

    insert_session_details(data.model_dump())

    return {
        "message": "Session details added successfully."
    }


@router.post("/add-problem-conversation")
def add_problem_conversation(data: ProblemConversation):

    insert_problem_conversation(data.model_dump())

    return {
        "message": "Problem conversation added successfully."
    }


@router.post("/add-session-results")
def add_session_results(data: SessionResults):

    insert_session_results(data.model_dump())

    return {
        "message": "Session results added successfully."
    }


@router.get("/session-results/{session_id}")
def read_session_results(session_id: str):
    result = get_session_results(session_id)

    if result is None:
        return {
            "session_id": session_id,
            "patterns": [],
            "recommendations": [],
        }

    return result
