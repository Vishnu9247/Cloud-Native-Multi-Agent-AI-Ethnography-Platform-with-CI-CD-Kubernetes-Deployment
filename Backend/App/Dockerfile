FROM python:3.11-slim

WORKDIR /Backend

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./App/main.py
COPY api ./App/api
COPY audio_utils ./App/audio_utils
COPY database_utils ./App/database_utils
COPY general_utils ./App/general_utils
COPY llm_utils ./App/llm_utils
COPY prompt_utils ./App/prompt_utils
COPY rag_utils ./App/rag_utils

EXPOSE 8000

CMD ["uvicorn", "App.main:app", "--host", "0.0.0.0", "--port", "8000"]
