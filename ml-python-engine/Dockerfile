# MediCanna AI - ML 推論服務 (Port 8000)
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .
EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=3)" || exit 1

CMD ["sh", "-c", "python bootstrap_models.py && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
