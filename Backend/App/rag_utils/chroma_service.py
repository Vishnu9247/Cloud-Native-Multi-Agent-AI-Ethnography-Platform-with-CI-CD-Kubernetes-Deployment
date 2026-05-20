import chromadb
import uuid
import json
from typing import Any

from chromadb.config import Settings

from App.general_utils.logging_config import get_logger


logger = get_logger(__name__)

chroma_client = chromadb.PersistentClient(
    path="./App/chroma_db",
    settings=Settings(
        anonymized_telemetry=False,
        chroma_product_telemetry_impl="App.rag_utils.chroma_telemetry.NoOpProductTelemetry",
        chroma_telemetry_impl="App.rag_utils.chroma_telemetry.NoOpProductTelemetry",
    ),
)

def create_vector_store(session_id: str):
    
    collection = chroma_client.get_or_create_collection(
        name=session_id
    )

    logger.info("chroma_collection_created session_id=%s", session_id)



def serialize_metadata_value(value: Any):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return json.dumps(value, ensure_ascii=False)


def add_doc(session_id: str, content: dict):
    
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
                "subdomain": tags[1] if isinstance(tags, list) and len(tags) > 1 else None,
                "tags": serialize_metadata_value(tags),
                "document_type": "subdomain_summary",
            }
        ],
    )
    logger.info("chroma_document_added session_id=%s domain=%s", session_id, domain)


def add_problem(session_id: str, problem: str):
    collection = chroma_client.get_collection(name = session_id)

    doc_id = f"{session_id}_problem"

    collection.upsert(
        ids=[doc_id],
        documents=[problem],
        metadatas=[
            {
                "session_id": session_id,
                "domain": "problem",
                "document_type": "problem",
            }
        ],
    )
    logger.info("chroma_problem_upserted session_id=%s", session_id)




def query_docs(session_id: str, query: str, n_results: int = 5):
    collection = chroma_client.get_collection(session_id)

    result = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    logger.info(
        "chroma_query_completed session_id=%s n_results=%s query_chars=%s",
        session_id,
        n_results,
        len(query),
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
                'domain': metadatas[i].get('domain'),
                'subdomain': metadatas[i].get('subdomain'),
                'document_type': metadatas[i].get('document_type'),
            }
        )
    return parsed_result


def delete_collection(session_id: str):
    try:
        chroma_client.delete_collection(name= session_id)
        logger.info("chroma_collection_deleted session_id=%s", session_id)
    except Exception:
        logger.exception("chroma_collection_delete_failed session_id=%s", session_id)
