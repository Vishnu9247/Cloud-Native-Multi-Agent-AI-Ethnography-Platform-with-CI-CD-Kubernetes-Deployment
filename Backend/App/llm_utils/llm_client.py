import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from langchain_ollama import ChatOllama

from App.general_utils.logging_config import get_logger


logger = get_logger(__name__)

DEFAULT_MODEL = os.getenv("LLM_MODEL", "llama3.2")
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
DEFAULT_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
DEFAULT_BACKOFF_SECONDS = float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "1.5"))
MAX_WORKERS = int(os.getenv("LLM_MAX_WORKERS", "4"))

_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


def create_chat_model(timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS):
    return ChatOllama(
        model=DEFAULT_MODEL,
        temperature=0,
        client_kwargs={"timeout": timeout_seconds},
    )


def _invoke_once(prompt: str, timeout_seconds: float):
    llm = create_chat_model(timeout_seconds=timeout_seconds)
    return llm.invoke(prompt).content.strip()


def invoke_llm(
    prompt: str,
    purpose: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> str:
    last_error = None

    for attempt in range(1, max_retries + 2):
        started_at = time.perf_counter()
        future = _executor.submit(_invoke_once, prompt, timeout_seconds)

        try:
            response = future.result(timeout=timeout_seconds)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            logger.info(
                "llm_call_success purpose=%s attempt=%s elapsed_ms=%s prompt_chars=%s response_chars=%s",
                purpose,
                attempt,
                elapsed_ms,
                len(prompt),
                len(response),
            )
            return response

        except TimeoutError as error:
            future.cancel()
            last_error = error
            logger.error(
                "llm_call_timeout purpose=%s attempt=%s timeout_seconds=%s prompt_chars=%s",
                purpose,
                attempt,
                timeout_seconds,
                len(prompt),
            )

        except Exception as error:
            last_error = error
            logger.exception(
                "llm_call_error purpose=%s attempt=%s prompt_chars=%s",
                purpose,
                attempt,
                len(prompt),
            )

        if attempt <= max_retries:
            time.sleep(DEFAULT_BACKOFF_SECONDS * attempt)

    raise RuntimeError(f"LLM call failed for {purpose}") from last_error
