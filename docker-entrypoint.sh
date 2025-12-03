#!/usr/bin/env bash
set -euo pipefail

# Start Ollama server in the background
ollama serve >/tmp/ollama.log 2>&1 &

# Wait for Ollama to become responsive
for i in {1..40}; do
  if curl -sf http://127.0.0.1:11434/api/tags >/dev/null; then
    break
  fi
  sleep 1
done

# Pull the desired model (cached inside the image)
ollama pull "${OLLAMA_MODEL:-llama3}"

# Seed the application data
python seed.py

# Launch the Flask app via gunicorn
exec gunicorn -b 0.0.0.0:5000 app:app
