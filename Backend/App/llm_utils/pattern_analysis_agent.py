from typing import List, Dict
from typing_extensions import TypedDict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
import json

from App.rag_utils.chroma_service import (
    query_docs, parse_query_result)
from App.prompt_utils.pattern_analysis_prompts import (
    PATTERN_DISCOVERY_QUESTION_GENERATOR,
    IDENTIFY_SOLID_PATTERNS,
    GENERATE_RECOMMENDATIONS
)


class AgentState(TypedDict):
    session_id: str
    problem: str
    domains: Dict[str, List[str]]
    pattern_questions: List[str]
    pattern_context: List[str]
    patterns: List[str]
    recommendations: List[str]


llm = ChatOllama(model="llama3.2", temperature=0)


def identify_pattern_question(state: AgentState) -> AgentState:

    prompt = PATTERN_DISCOVERY_QUESTION_GENERATOR.format(
        problem=state['problem'],
        domains=state['domains']
    )

    response = llm.invoke(prompt).content.strip()

    try:
        questions = json.loads(response)

        if not isinstance(questions, list):
            questions = []

    except Exception as e:
        print("Error parsing questions:", e)
        questions = []

    state['pattern_questions'] = questions

    return state



def get_pattern_data(state: AgentState) -> AgentState:

    pattern_questions = state['pattern_questions']

    all_context = []
    seen_ids = set()

    for question in pattern_questions:
        context = parse_query_result(
            query_docs(
                session_id=state['session_id'],
                query=question
            )
        )
        for item in context:
            if item['id'] not in seen_ids:
                seen_ids.add(item['id'])
                all_context.append(item)
    state['pattern_context'] = all_context

    return state



def identify_patterns(state: AgentState) -> AgentState:

    prompt = IDENTIFY_SOLID_PATTERNS.format(
        problem=state["problem"],
        pattern_questions=json.dumps(
            state["pattern_questions"],
            indent=2
        ),
        pattern_context=json.dumps(
            state["pattern_context"],
            indent=2
        )
    )

    response = llm.invoke(prompt).content.strip()

    try:
        patterns = json.loads(response)

        if not isinstance(patterns, list):
            patterns = []

        patterns = [
            pattern.strip()
            for pattern in patterns
            if isinstance(pattern, str) and pattern.strip()
        ]

    except Exception as e:
        print("Error parsing patterns:", e)
        print("Raw response:", response)
        patterns = []

    state["patterns"] = patterns

    return state




def generate_recommendations(state: AgentState) -> AgentState:

    prompt = GENERATE_RECOMMENDATIONS.format(
        problem=state["problem"],
        patterns=json.dumps(
            state["patterns"],
            indent=2
        ),
        pattern_context=json.dumps(
            state["pattern_context"],
            indent=2
        )
    )
    response = llm.invoke(prompt).content.strip()

    try:
        recommendations = json.loads(response)

        if not isinstance(recommendations, list):
            recommendations = []

        recommendations = [
            recommendation.strip()
            for recommendation in recommendations
            if isinstance(recommendation, str) and recommendation.strip()
        ]
    except Exception as e:
        print("Error parsing recommendations:", e)
        print("Raw response:", response)
        recommendations = []

    state["recommendations"] = recommendations

    return state




graph = StateGraph(AgentState)

graph.add_node('identify_pattern_question', identify_pattern_question)
graph.add_node('get_pattern_data', get_pattern_data)
graph.add_node('identify_patterns', identify_patterns)
graph.add_node('generate_recommendations', generate_recommendations)

graph.set_entry_point('identify_pattern_question')
graph.add_edge('identify_pattern_question', 'get_pattern_data')
graph.add_edge('get_pattern_data', 'identify_patterns')
graph.add_edge('identify_patterns','generate_recommendations')
graph.add_edge('generate_recommendations', END)

app = graph.compile()