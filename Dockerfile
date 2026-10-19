FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production APPLICATION_ASSISTANT_ENABLED=false \
    HF_HOME=/tmp/huggingface JOB_DATA_DIR=/data
WORKDIR /app
RUN useradd --create-home --uid 1000 appuser
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser *.py ./
USER appuser
EXPOSE 7860
CMD ["python", "cloud_entrypoint.py"]
