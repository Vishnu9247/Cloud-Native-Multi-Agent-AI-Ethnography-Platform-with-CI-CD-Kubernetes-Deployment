import chromadb
import uuid
from chromadb.config import Settings

chroma_client = chromadb.PersistentClient(path="./App/chroma_db")

def create_vector_store(session_id: str):
    
    collection = chroma_client.get_or_create_collection(
        name=session_id
    )

    print(f'Collection {session_id} Created')



def add_doc(session_id: str, content: str):
    
    collection = chroma_client.get_collection(name = session_id)

    domain = content['domain']
    tags = content['tags']
    doc_id = f"{session_id}_{domain}_{uuid.uuid4().hex}"

    collection.add(
        ids=[doc_id],
        documents=[content['summary']],
        metadatas=[
            {
                "session_id": session_id,
                "domain": domain,
                "tags": tags
            }
        ],
    )



def query_docs(session_id: str, query: str, n_results: int = 5):
    collection = chroma_client.get_collection(session_id)

    result = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    return result




def parse_query_result(result: dict) -> list:

    parsed_result = []

    ids = result.get('ids', [[]])[0]
    documents = result.get('documents', [[]])[0]
    metadatas = result.get('metadatas', [[]])[0]
    distances = result.get('distances', [[]])[0]

    for i in range(len(documents)):
        parsed_result.append(
            {
                'id': ids[i],
                'document': documents[i],
                'domain': metadatas[i].get('domain')
            }
        )
    return parsed_result


def delete_collection(session_id: str):
    chroma_client.delete_collection(name= session_id)
    print(f"Session {session_id} deleted")