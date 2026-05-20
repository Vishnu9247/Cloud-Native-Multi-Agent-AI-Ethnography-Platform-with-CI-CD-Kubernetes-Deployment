import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from App.api.routes.vector_store import router as vector_router
from App.api.routes.audio import router as audio_router
from App.api.routes.agent_one import router as problem_framing_router
from App.api.routes.agent_two import router as domain_selection_router
from App.api.routes.agent_three import router as interview_router
from App.api.routes.agent_four import router as identify_patterns
from App.api.routes.database import router as database_operations
from App.database_utils.data_loader import ensure_database
from App.general_utils.logging_config import configure_logging, get_logger


configure_logging()
logger = get_logger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    ensure_database()
    logger.info("application_startup_complete")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.exception(
            "request_failed request_id=%s method=%s path=%s elapsed_ms=%s",
            request_id,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed request_id=%s method=%s path=%s status_code=%s elapsed_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception(
        "unhandled_exception request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": exc.__class__.__name__,
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(vector_router, prefix = '/vector', tags = ['Vector Store'])
app.include_router(audio_router, prefix = '/audio', tags = ['Audio'])
app.include_router(problem_framing_router, prefix = '/agent', tags = ['Problem Framing Agent'])
app.include_router(domain_selection_router, prefix = '/agent', tags = ['Domain Selection Agent'])
app.include_router(interview_router, prefix= '/agent', tags= ['Interview Agent'])
app.include_router(identify_patterns, prefix='/agent', tags = ['Pattern Identification'])
app.include_router(database_operations, prefix= '/database', tags = ['Database'])
