from fastapi import APIRouter
from pydantic import BaseModel
from App.rag_utils.chroma_service import (
    create_vector_store, add_doc, query_docs, 
    parse_query_result, delete_collection,
    add_problem)

router = APIRouter()


class CreateVectorStoreRequest(BaseModel):
    session_id: str


class AddDocumentRequest(BaseModel):
    session_id: str
    content: object


class QueryDocumentsRequest(BaseModel):
    session_id: str
    query: str

class ProblemStoreRequest(BaseModel):
    session_id: str
    problem: str

@router.post('/create')
def create_chromadb(doc: CreateVectorStoreRequest):
    create_vector_store(session_id= doc.session_id)
    return {"session_id": doc.session_id, "status": "created"}

@router.post('/add_docs')
def add_docs_to_chromadb(doc: AddDocumentRequest):
    add_doc(session_id= doc.session_id, content= doc.content)
    return {"session_id": doc.session_id, "status": "added"}

@router.post('/add_problem')
def add_problem_to_collection(doc: ProblemStoreRequest):
    add_problem(session_id= doc.session_id, problem= doc.problem)
    return {"session_id": doc.session_id, "status": "added"}

@router.post('/get_docs')
def get_docs_from_chromadb(doc: QueryDocumentsRequest):
    result = query_docs(session_id= doc.session_id, query= doc.query)
    result_parsed = parse_query_result(result= result)
    return result_parsed

@router.post('/delete_collection')
def end_session(doc: CreateVectorStoreRequest):
    delete_collection(session_id= doc.session_id)
    return {"session_id": doc.session_id, "status": "deleted"}