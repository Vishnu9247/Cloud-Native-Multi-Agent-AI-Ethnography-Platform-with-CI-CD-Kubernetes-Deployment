from typing import List, Dict
from typing_extensions import TypedDict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
import json
from App.prompt_utils.domain_selection_prompts import DOMAIN_SELECTION
from App.rag_utils.chroma_service import query_docs, parse_query_result, create_vector_store


llm = ChatOllama(model="llama3.2", temperature=0)

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
    response = llm.invoke(prompt).content.strip()

    try:
        domains = json.loads(response)

    except Exception as e:
        print("Error parsing domains:", e)
        domains = {}

    state['domains'] = domains
    print(domains)
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