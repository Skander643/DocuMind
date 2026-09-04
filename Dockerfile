FROM python:3.12-slim

WORKDIR /src

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# CPU wheel first so sentence-transformers does not pull CUDA torch.
RUN pip install --no-cache-dir torch==2.6.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements-phase0.txt backend/requirements-docker.txt /tmp/
ENV PIP_DEFAULT_TIMEOUT=180
RUN pip install --no-cache-dir --retries 15 -r /tmp/requirements-docker.txt

COPY backend /src/backend
COPY eval /src/eval
COPY data/raw /src/data/raw
COPY data/chroma /src/data/chroma
COPY data/processed /src/data/processed

WORKDIR /src/backend
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/src/backend
ENV HF_HOME=/root/.cache/huggingface
ENV APP_ENV=prod
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
