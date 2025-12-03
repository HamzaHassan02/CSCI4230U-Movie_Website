FROM python:3.11-slim

# Prevent Python from writing pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies (for bcrypt and similar packages) and curl (for Ollama)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libssl-dev \
    libffi-dev \
    curl \
    bash \
 && rm -rf /var/lib/apt/lists/*

# Install Ollama CLI (used to pull models + serve)
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Install Python dependencies first
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default Flask/Gunicorn configuration
ENV FLASK_APP=app.py \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000 \
    OLLAMA_MODEL=gemma3:1b

EXPOSE 5000

# Entry: start Ollama, pull the model, seed the DB, then start gunicorn
RUN chmod +x ./docker-entrypoint.sh
ENTRYPOINT ["./docker-entrypoint.sh"]
