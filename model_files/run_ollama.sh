#!/bin/sh
set -e

echo "Starting Ollama server..."
ollama serve &

echo "Waiting for Ollama API to become available..."
until ollama list >/dev/null 2>&1; do
  sleep 1
done

echo "Ollama is ready."

MODEL_NAME=finetuned_mistral
GGUF_PATH=/model_files/mistral-7b-instruct-v0.1.Q2_K.gguf
MODELFIELD=/model_files/Modelfile

if ollama list | grep -q "$MODEL_NAME"; then
  echo "Model '$MODEL_NAME' already exists. Skipping creation."
else
  echo "Creating model '$MODEL_NAME'..."
  ollama create "$MODEL_NAME" -f "$MODELFIELD"
fi

echo "Ollama is running and ready."
wait


