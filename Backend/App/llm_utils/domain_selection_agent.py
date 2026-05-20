from typing import List, Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
import json
from App.prompt_utils.domain_selection_prompts import DOMAIN_SELECTION
from App.rag_utils.chroma_service import query_docs, parse_query_result, create_vector_store
from App.llm_utils.llm_client import invoke_llm
from App.general_utils.logging_config import get_logger


logger = get_logger(__name__)

class ChatMessage:
    role: str
    content: str


class AgentState(TypedDict):
    session_id : str
    problem : str
    domains : Dict[str, List[str]]

def domain_selection(state: AgentState) -> AgentState:

    prompt = DOMAIN_SELECTION.format(
        problem = state['problem']
    )
    response = invoke_llm(prompt, purpose="domain_selection.select_domains")
    try:
        domains = json.loads(response)

    except Exception:
        logger.exception("domain_selection_parse_error")
        domains = {}

    state['domains'] = domains
    logger.info("domain_selection_completed session_id=%s domain_count=%s", state["session_id"], len(domains))
    return state

graph = StateGraph(AgentState)

graph.add_node('domain_selection', domain_selection,)
graph.add_node('frontend', lambda state: state,)

graph.set_entry_point('domain_selection')
graph.add_edge('domain_selection', 'frontend')
graph.add_edge('frontend', END)

app = graph.compile()    

# if __name__ == "__main__":
#     initial_state: AgentState = {
#         'session_id' : 'vishnu_123',
#         'problem' : 'I am not finding motivation to study or apply for jobs. My financial status is not good. And Yet, i am just passing time watching movies and doing courses',
#         'domains' : {},
#         'conversations' : [],
#         'is_complete' : False,
#         'summary': ''
#     }

#     create_vector_store(session_id = initial_state['session_id'] )
#     state_one = domain_selection(initial_state)
