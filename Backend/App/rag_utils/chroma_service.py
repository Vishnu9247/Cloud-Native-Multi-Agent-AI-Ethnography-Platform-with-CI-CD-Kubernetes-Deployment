import json
import os
import uuid
from typing import Any

import chromadb
from chromadb.config import Settings

from App.general_utils.logging_config import get_logger


logger = get_logger(__name__)

_chroma_client = None


def _chroma_settings():
    return Settings(
        anonymized_telemetry=False,
        chroma_product_telemetry_impl="App.rag_utils.chroma_telemetry.NoOpProductTelemetry",
        chroma_telemetry_impl="App.rag_utils.chroma_telemetry.NoOpProductTelemetry",
    )


def get_chroma_client():
    global _chroma_client

    if _chroma_client is not None:
        return _chroma_client

    host = os.getenv("CHROMA_HOST")

    if host:
        _chroma_client = chromadb.HttpClient(
            host=host,
            port=int(os.getenv("CHROMA_PORT", "8000")),
            ssl=os.getenv("CHROMA_SSL", "false").lower() == "true",
            settings=_chroma_settings(),
        )
        return _chroma_client

    _chroma_client = chromadb.PersistentClient(
        path=os.getenv("CHROMA_PERSIST_PATH", "./App/local_chroma_db"),
        settings=_chroma_settings(),
    )
    return _chroma_client


def ensure_chroma_ready():
    client = get_chroma_client()
    heartbeat = getattr(client, "heartbeat", None)
    if callable(heartbeat):
        heartbeat()
    return True


def create_vector_store(session_id: str):
    collection = get_chroma_client().get_or_create_collection(name=session_id)

    logger.info("chroma_collection_created session_id=%s", session_id)
    return collection



def serialize_metadata_value(value: Any):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return json.dumps(value, ensure_ascii=False)


def clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            cleaned[key] = ""
        else:
            cleaned[key] = serialize_metadata_value(value)
    return cleaned


def get_session_collection(session_id: str):
    return get_chroma_client().get_or_create_collection(name=session_id)


def add_doc(session_id: str, content: dict):
    collection = get_session_collection(session_id)

    domain = content['domain']
    tags = content['tags']
    doc_id = f"{session_id}_{domain}_{uuid.uuid4().hex}"

    collection.add(
        ids=[doc_id],
        documents=[content['summary']],
        metadatas=[
            clean_metadata({
                "session_id": session_id,
                "domain": domain,
                "subdomain": tags[1] if isinstance(tags, list) and len(tags) > 1 else None,
                "tags": serialize_metadata_value(tags),
                "document_type": "subdomain_summary",
            })
        ],
    )
    logger.info("chroma_document_added session_id=%s domain=%s", session_id, domain)


def add_problem(session_id: str, problem: str):
    collection = get_session_collection(session_id)

    doc_id = f"{session_id}_problem"

    collection.upsert(
        ids=[doc_id],
        documents=[problem],
        metadatas=[
            clean_metadata({
                "session_id": session_id,
                "domain": "problem",
                "document_type": "problem",
            })
        ],
    )
    logger.info("chroma_problem_upserted session_id=%s", session_id)


def add_conversation_message(
    session_id: str,
    role: str,
    content: str,
    stage: str = "",
    domain: str = "",
    subdomain: str = "",
    metadata: dict[str, Any] | None = None,
):
    collection = get_session_collection(session_id)
    doc_id = f"{session_id}_message_{uuid.uuid4().hex}"
    base_metadata = {
        "session_id": session_id,
        "role": role,
        "stage": stage,
        "domain": domain,
        "subdomain": subdomain,
        "document_type": "conversation_message",
    }

    if metadata:
        base_metadata.update(metadata)

    collection.add(
        ids=[doc_id],
        documents=[content],
        metadatas=[clean_metadata(base_metadata)],
    )
    return doc_id




def query_docs(session_id: str, query: str, n_results: int = 5):
    collection = get_session_collection(session_id)

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
                'role': metadatas[i].get('role'),
                'stage': metadatas[i].get('stage'),
                'document_type': metadatas[i].get('document_type'),
            }
        )
    return parsed_result


def delete_collection(session_id: str):
    try:
        get_chroma_client().delete_collection(name=session_id)
        logger.info("chroma_collection_deleted session_id=%s", session_id)
    except Exception:
        logger.exception("chroma_collection_delete_failed session_id=%s", session_id)
