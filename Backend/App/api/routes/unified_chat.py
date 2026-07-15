from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from App.unified_chat.workflow import (
    create_session,
    generate_results,
    handle_user_message,
)


router = APIRouter()


class CreateSessionRequest(BaseModel):
    name: str = Field(min_length=1)
    age: int = Field(gt=0, le=120)


class ChatMessageRequest(BaseModel):
    state: dict[str, Any]
    message: str = Field(min_length=1)


class ResultsRequest(BaseModel):
    state: dict[str, Any]


def response_from_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "session": {
            "session_id": state.get("session_id"),
            "name": state.get("name"),
            "age": state.get("age"),
        },
        "state": state,
        "stage": state.get("stage"),
        "messages": state.get("conversation", []),
        "events": state.get("events", []),
        "last_event": state.get("last_event", {}),
        "patterns": state.get("patterns", []),
        "recommendations": state.get("recommendations", []),
    }


@router.post("/session")
def start_session(request: CreateSessionRequest):
    state = create_session(name=request.name, age=request.age)
    return response_from_state(state)


@router.post("/message")
def send_message(request: ChatMessageRequest):
    state = handle_user_message(request.state, request.message)
    return response_from_state(state)


@router.post("/results")
def create_results(request: ResultsRequest):
    state = generate_results(request.state)
    return response_from_state(state)
