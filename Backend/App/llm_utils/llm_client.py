import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from openai import AzureOpenAI

from App.general_utils.logging_config import get_logger


logger = get_logger(__name__)

DEFAULT_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://ethnography-llm-endpoint.cognitiveservices.azure.com/",
)
DEFAULT_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
DEFAULT_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_DEPLOYMENT",
    os.getenv("AZURE_OPENAI_MODEL", os.getenv("LLM_MODEL", "gpt-5.4-mini")),
)
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
DEFAULT_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
DEFAULT_BACKOFF_SECONDS = float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "1.5"))
DEFAULT_MAX_COMPLETION_TOKENS = int(os.getenv("LLM_MAX_COMPLETION_TOKENS", "16384"))
MAX_WORKERS = int(os.getenv("LLM_MAX_WORKERS", "4"))

_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


def normalize_azure_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip()

    for suffix in ("/openai/v1/", "/openai/v1", "/openai/"):
        if endpoint.endswith(suffix):
            endpoint = endpoint[: -len(suffix)]
            break

    return endpoint.rstrip("/") + "/"


def get_api_key() -> str:
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Missing Azure OpenAI API key. Set AZURE_OPENAI_API_KEY as an environment variable."
        )

    return api_key


def create_openai_client(timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS):
    return AzureOpenAI(
        api_version=DEFAULT_API_VERSION,
        azure_endpoint=normalize_azure_endpoint(DEFAULT_ENDPOINT),
        api_key=get_api_key(),
        timeout=timeout_seconds,
        max_retries=0,
    )


def _invoke_once(prompt: str, timeout_seconds: float):
    client = create_openai_client(timeout_seconds=timeout_seconds)
    completion = client.chat.completions.create(
        model=DEFAULT_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "You are an expert ethnography interview assistant. Return only the requested content.",
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_completion_tokens=DEFAULT_MAX_COMPLETION_TOKENS,
    )

    message = completion.choices[0].message
    content = message.content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text") or item.get("content") or "")
            else:
                parts.append(getattr(item, "text", "") or getattr(item, "content", ""))

        content = "".join(parts)

    if not content:
        raise RuntimeError("Azure OpenAI returned an empty response.")

    return content.strip()


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
                "llm_call_success provider=azure_openai endpoint=%s api_version=%s deployment=%s purpose=%s attempt=%s elapsed_ms=%s prompt_chars=%s response_chars=%s",
                normalize_azure_endpoint(DEFAULT_ENDPOINT),
                DEFAULT_API_VERSION,
                DEFAULT_DEPLOYMENT,
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
                "llm_call_timeout provider=azure_openai endpoint=%s api_version=%s deployment=%s purpose=%s attempt=%s timeout_seconds=%s prompt_chars=%s",
                normalize_azure_endpoint(DEFAULT_ENDPOINT),
                DEFAULT_API_VERSION,
                DEFAULT_DEPLOYMENT,
                purpose,
                attempt,
                timeout_seconds,
                len(prompt),
            )

        except Exception as error:
            last_error = error
            logger.exception(
                "llm_call_error provider=azure_openai endpoint=%s api_version=%s deployment=%s purpose=%s attempt=%s prompt_chars=%s",
                normalize_azure_endpoint(DEFAULT_ENDPOINT),
                DEFAULT_API_VERSION,
                DEFAULT_DEPLOYMENT,
                purpose,
                attempt,
                len(prompt),
            )

        if attempt <= max_retries:
            time.sleep(DEFAULT_BACKOFF_SECONDS * attempt)

    raise RuntimeError(f"LLM call failed for {purpose}") from last_error
