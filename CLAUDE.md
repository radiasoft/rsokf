# Local Ollama OKF Reader Project Brief

## Goal

Develop a Python program that can answer questions about an Open Knowledge Format
repository using Ollama.

## Projex

Fill out

For more than a few files, do not paste the entire directory into
every prompt. Put a small retrieval layer in front of Ollama:

OKF directory
    |
Markdown/YAML parser
    |
embedding index
    |
retrieve relevant files/sections
    |
Qwen3 8B

A simple implementation could use Python, Ollama’s local API, and
SQLite with vector search. Ollama exposes an OpenAI-compatible API at
localhost:11434, so existing OpenAI client code can usually point at
it with minimal changes.




`OLLAMA_FLASH_ATTENTION="1" OLLAMA_KV_CACHE_TYPE="q8_0" ~/brew/opt/ollama/bin/ollama serve`



retirement simulator and optimizer that produces
a financially correct year-by-year simulation and then optimizes
retirement decisions.

Financial correctness takes priority over optimization.
