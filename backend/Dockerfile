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

WORKDIR /src/backend
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/src/backend
ENV HF_HOME=/root/.cache/huggingface
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
