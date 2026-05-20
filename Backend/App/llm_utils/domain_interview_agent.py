import json
from typing import List, Dict
from typing_extensions import TypedDict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from App.prompt_utils.domain_interview_prompts import DOMAIN_EXPLORER, QUERY_AND_REPHRASE
from App.llm_utils.interview_validation_agent import app as validation_app
from App.rag_utils.chroma_service import query_docs, parse_query_result
#from App.llm_utils.llm_initialization import get_response





llm = ChatOllama(model="llama3.2", temperature=0)


class ChatMessage(TypedDict):
    role: str
    content: str


class AgentState(TypedDict):
    session_id: str
    problem: str

    domains_to_explore: Dict[str, List[str]]
    domains_explored: Dict[str, List[str]]

    current_domain: str
    current_subdomain: str
    current_questions: List[str]

    conversations: List[ChatMessage]
    is_complete: bool
    followup_message: str
    summary: str
    summaries: Dict[str, str]


def get_next_domain_subdomain(state: AgentState):
    for domain, subdomains in state["domains_to_explore"].items():
        if subdomains:
            return domain, subdomains[0]

    return None, None


def clean_json_response(response: str) -> str:
    return (
        response
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )


def domain_explorer(state: AgentState) -> AgentState:
    domain, subdomain = get_next_domain_subdomain(state)

    if domain is None:
        state["is_complete"] = True
        return state

    prompt = DOMAIN_EXPLORER.format(
        problem=state["problem"],
        domain=domain,
        subdomain=subdomain,
    )

    response = llm.invoke(prompt).content.strip()
    response = clean_json_response(response)

    parsed_output = json.loads(response)

    questions = parsed_output.get("questions", [])

    questions = [
        q[0] if isinstance(q, list) else q
        for q in questions
    ]

    questions = [
        q.strip()
        for q in questions
        if isinstance(q, str) and q.strip()
    ]

    state["current_domain"] = parsed_output.get("domain", domain)
    state["current_subdomain"] = parsed_output.get("subdomain", subdomain)
    state["current_questions"] = questions

    state["conversations"] = []
    state["is_complete"] = False
    state["followup_message"] = ""
    state["summary"] = ""

    return state


def query_and_rephrase(state: AgentState) -> AgentState:
    rephrased_questions = []

    domain = state["current_domain"]
    subdomain = state["current_subdomain"]
    questions = state["current_questions"]
    session_id = state["session_id"]

    for question in questions:
        try:
            query_result = query_docs(
                session_id=session_id,
                query=question,
            )

            previous_interactions = parse_query_result(query_result)

        except Exception as e:
            print(f"Vector store query skipped: {e}")
            rephrased_questions.append(question)
            continue

        if not previous_interactions:
            rephrased_questions.append(question)
            continue

        context = ""

        for item in previous_interactions:
            context += f"""
Previous document: {item["document"]}
Domain: {item["domain"]}
"""

        prompt = QUERY_AND_REPHRASE.format(
            domain=domain,
            subdomain=subdomain,
            question=question,
            context=context,
        )

        rephrased_question = response = llm.invoke(prompt).content.strip()
        rephrased_questions.append(rephrased_question)

    state["current_questions"] = rephrased_questions

    return state


def validate_user_answers(state: AgentState) -> AgentState:
    validation_state = {
        "session_id": state["session_id"],
        "problem": state["problem"],
        "domain": state["current_domain"],
        "subdomain": state["current_subdomain"],
        "conversations": state["conversations"],
        "is_complete": False,
        "followup_message": "",
        "summary": "",
    }

    result = validation_app.invoke(validation_state)

    state["is_complete"] = result["is_complete"]
    state["followup_message"] = result["followup_message"]
    state["conversations"] = result["conversations"]

    if result["is_complete"]:
        domain = state["current_domain"]
        subdomain = state["current_subdomain"]

        state["summary"] = result["summary"]

        summary_key = f"{domain}:{subdomain}"
        state["summaries"][summary_key] = result["summary"]

        if domain not in state["domains_explored"]:
            state["domains_explored"][domain] = []

        if subdomain not in state["domains_explored"][domain]:
            state["domains_explored"][domain].append(subdomain)

        if domain in state["domains_to_explore"]:
            if subdomain in state["domains_to_explore"][domain]:
                state["domains_to_explore"][domain].remove(subdomain)

            if not state["domains_to_explore"][domain]:
                del state["domains_to_explore"][domain]

        state["current_domain"] = ""
        state["current_subdomain"] = ""
        state["current_questions"] = []
        state["conversations"] = []
        state["followup_message"] = ""

    return state


graph = StateGraph(AgentState)

graph.add_node("domain_explorer", domain_explorer)
graph.add_node("query_and_rephrase", query_and_rephrase)

graph.set_entry_point("domain_explorer")

graph.add_edge("domain_explorer", "query_and_rephrase")
graph.add_edge("query_and_rephrase", END)

app = graph.compile()