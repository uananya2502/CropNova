# The application is Python-based; the encoder runs locally on CPU.
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 CROPNOVA_MODEL_CACHE=/opt/cropnova-models \
    CROPNOVA_DATA_DIR=/data PORT=8000 AI_PROVIDER=gemini
WORKDIR /app
COPY requirements.txt ./
# The CPU wheel avoids installing unnecessary CUDA libraries on a web host.
RUN python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.10.0 \
    && python -m pip install -r requirements.txt
COPY *.py ./
COPY knowledge_base/ ./knowledge_base/
COPY rule_engine/ ./rule_engine/
COPY static/ ./static/
COPY scripts/ ./scripts/
# Download only at build time, never from a user's request.
RUN python scripts/prepare_transformer.py \
    && useradd --uid 10001 --create-home cropnova \
    && mkdir -p /data \
    && chown cropnova:cropnova /data \
    && chmod 700 /data
ENV HF_HUB_OFFLINE=1
USER cropnova
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/ready', timeout=3)"
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:application"]
