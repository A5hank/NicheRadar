FROM docker.io/library/python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN python -m pip install --no-cache-dir --editable .

COPY frontend/ ./frontend/

RUN mkdir -p /app/data \
    && useradd --create-home --uid 10001 nicheradar \
    && chown -R nicheradar:nicheradar /app

USER nicheradar

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "nicheradar.api:app", "--host", "0.0.0.0", "--port", "8000"]