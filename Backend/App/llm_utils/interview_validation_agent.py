from typing import List
from typing_extensions import TypedDict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from App.prompt_utils.interview_validation_prompts import IDENTIFY_GAPS, SUMMARY_PROMPT
from App.rag_utils.chroma_service import add_doc
#from App.llm_utils.llm_initialization import get_response


llm = ChatOllama(model="llama3.2", temperature=0)


class ChatMessage(TypedDict):
    role: str
    content: str


class ValidationState(TypedDict):
    session_id: str
    problem: str
    domain: str
    subdomain: str
    conversations: List[ChatMessage]
    is_complete: bool
    followup_message: str
    summary: str


def format_conversation(conversations: List[ChatMessage]) -> str:
    return "\n\n".join(
        f"{message['role'].upper()}: {message['content']}"
        for message in conversations
    )


def parse_validation_status(response: str) -> str:
    text = response.strip().lower()

    if "status: incomplete" in text:
        return "incomplete"

    if "status: complete" in text:
        return "complete"

    # fallback for older prompt behavior
    if "incomplete" in text:
        return "incomplete"

    if "complete" in text:
        return "complete"

    return "unknown"


def clean_followup_message(response: str) -> str:
    lines = response.splitlines()

    cleaned_lines = [
        line for line in lines
        if not line.strip().lower().startswith("status:")
    ]

    return "\n".join(cleaned_lines).strip()


def identify_gaps(state: ValidationState) -> ValidationState:
    conversation_text = format_conversation(state["conversations"])

    prompt = IDENTIFY_GAPS.format(
        problem=state["problem"],
        domain=state["domain"],
        subdomain=state["subdomain"],
        conversation_text=conversation_text,
    )

    response = llm.invoke(prompt).content.strip()

    status = parse_validation_status(response)

    if status == "complete":
        state["is_complete"] = True
        state["followup_message"] = ""
        return state

    if status == "incomplete":
        followup_message = clean_followup_message(response)

        state["is_complete"] = False
        state["followup_message"] = followup_message

        state["conversations"].append(
            {
                "role": "assistant",
                "content": followup_message,
            }
        )

        return state

    # Safe fallback:
    # If model gives unclear output, treat it as incomplete
    # and send the message to frontend.
    state["is_complete"] = False
    state["followup_message"] = response

    state["conversations"].append(
        {
            "role": "assistant",
            "content": response,
        }
    )

    return state


def summarize_conversation(state: ValidationState) -> ValidationState:
    conversation_text = format_conversation(state["conversations"])

    prompt = SUMMARY_PROMPT.format(
        problem=state["problem"],
        domain=state["domain"],
        subdomain=state["subdomain"],
        conversation_text=conversation_text,
    )

    summary = llm.invoke(prompt).content.strip()

    state["summary"] = summary
    state["is_complete"] = True

    try:
        vector_document = {
            "domain": state["domain"],
            "tags": [
                state["domain"],
                state["subdomain"],
            ],
            "summary": summary,
        }

        add_doc(
            session_id=state["session_id"],
            content=vector_document,
        )

        print("Summary added to vector store")

    except Exception as e:
        print("Failed to add summary to vector store")
        print(e)

    return state


def route_after_validation(state: ValidationState) -> str:
    if state["is_complete"]:
        return "summarize_conversation"

    return "end"


graph = StateGraph(ValidationState)

graph.add_node("identify_gaps", identify_gaps)
graph.add_node("summarize_conversation", summarize_conversation)

graph.set_entry_point("identify_gaps")

graph.add_conditional_edges(
    "identify_gaps",
    route_after_validation,
    {
        "summarize_conversation": "summarize_conversation",
        "end": END,
    },
)

graph.add_edge("summarize_conversation", END)

app = graph.compile()