# VigilCloud on Akamai LKE.
# Build from this directory so the cluster nodes can run it:
#   docker build --platform linux/amd64 -t YOUR_REGISTRY/vigilcloud:latest .
# Settings come from the pod environment (secret app-env). Never copy .env into the image.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY settings.py db.py storage.py inference_verifier.py sample_catalog.py app.py ./
COPY samples ./samples
COPY .streamlit ./.streamlit

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4)"

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
