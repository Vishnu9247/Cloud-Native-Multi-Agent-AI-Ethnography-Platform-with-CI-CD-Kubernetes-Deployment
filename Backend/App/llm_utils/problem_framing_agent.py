from typing import List
from typing_extensions import TypedDict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from App.prompt_utils.problem_framing_prompts import (
    CHECK_COMPLETENESS_AND_IDENTIFY_GAPS,
    SUMMARIZE_PROBLEM,
)
#from App.llm_utils.llm_initialization import get_response



llm = ChatOllama(model="llama3.2", temperature=0)


class ChatMessage(TypedDict):
    role: str
    content: str


class AgentState(TypedDict):
    session_id: str
    name: str
    age: str
    problem_conversation: List[ChatMessage]
    summary: str
    is_complete: bool


def format_conversation(conversation: List[ChatMessage]) -> str:
    formatted_text = ""

    for message in conversation:
        formatted_text += f"{message['role'].upper()}: {message['content']}\n\n"

    return formatted_text.strip()


def check_completeness_and_identify_gaps(state: AgentState) -> AgentState:

    user_message_count = len([
        m for m in state["problem_conversation"]
        if m["role"] == "user"
    ])

    # Hard stop to avoid endless loops
    if user_message_count >= 3:
        state["is_complete"] = True
        return state

    conversation_text = format_conversation(state["problem_conversation"])

    prompt = CHECK_COMPLETENESS_AND_IDENTIFY_GAPS.format(
        name=state["name"],
        age=state["age"],
        conversation_text=conversation_text,
    )

    response = llm.invoke(prompt).content.strip()
    normalized_response = response.lower().strip(" .!")

    if normalized_response == "complete":
        state["is_complete"] = True
        return state

    state["is_complete"] = False

    state["problem_conversation"].append(
        {
            "role": "assistant",
            "content": response,
        }
    )

    return state





def summarize_problem(state: AgentState) -> AgentState:
    conversation_text = format_conversation(state["problem_conversation"])

    prompt = SUMMARIZE_PROBLEM.format(
        name=state["name"],
        age=state["age"],
        conversation_text=conversation_text,
    )

    response = llm.invoke(prompt).content.strip()

    state["summary"] = response
    state["is_complete"] = True

    return state


def route_after_completeness_check(state: AgentState) -> str:
    if state["is_complete"]:
        return "summarize"

    return "frontend"



graph_builder = StateGraph(AgentState)

graph_builder.add_node(
    "check_completeness_and_identify_gaps",
    check_completeness_and_identify_gaps,
)

graph_builder.add_node(
    "summarize_problem",
    summarize_problem,
)

graph_builder.add_node(
    "frontend",
    lambda state: state,
)

graph_builder.set_entry_point("check_completeness_and_identify_gaps")

graph_builder.add_conditional_edges(
    "check_completeness_and_identify_gaps",
    route_after_completeness_check,
    {
        "summarize": "summarize_problem",
        "frontend": "frontend",
    },
)

graph_builder.add_edge("frontend", END)
graph_builder.add_edge("summarize_problem", END)

app = graph_builder.compile()


# if __name__ == "__main__":
#     initial_state: AgentState = {
#         "session_id": "session_001",
#         "name": "Vishnu",
#         "age": "24",
#         "problem_conversation": [{"role": 'user',
#                                   'content': 'I am not finding motivation to study or apply for jobs. My financial status is not good. And Yet, i am just passing time watching movies and doing courses'}],
#         "summary": "",
#         "is_complete": False
#     }

#     final_state = app.invoke(initial_state)

#     print("\nFinal Summary")
#     print("=" * 50)
#     print(final_state["summary"])
