import os
import time

import requests

from App.general_utils.logging_config import get_logger


logger = get_logger(__name__)

model_name = 'llama3.2'

url = "http://localhost:11434/api/generate"

REQUEST_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
BACKOFF_SECONDS = float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "1.5"))


def get_response(prompt):
    payload = {
        "model": 'llama3.2',
        "prompt": prompt,
        "stream" : False
        }

    last_error = None

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            result = requests.post(
                url,
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ).json()
            response = result['response']
            logger.info(
                "legacy_ollama_call_success attempt=%s prompt_chars=%s response_chars=%s",
                attempt,
                len(prompt),
                len(response),
            )
            return response.strip()

        except Exception as error:
            last_error = error
            logger.exception(
                "legacy_ollama_call_failed attempt=%s prompt_chars=%s",
                attempt,
                len(prompt),
            )

        if attempt <= MAX_RETRIES:
            time.sleep(BACKOFF_SECONDS * attempt)

    raise RuntimeError("Legacy Ollama call failed") from last_error
