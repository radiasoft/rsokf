"""Thin client for the local Ollama HTTP API.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkdebug import pkdc, pkdlog, pkdp
import requests
import rsokf.config


def chat(messages):
    """Ask the configured Ollama chat model to respond to `messages`

    Args:
        messages (list): PKDict(role=, content=) in conversation order

    Returns:
        str: the assistant's reply text
    """
    r = requests.post(
        rsokf.config.cfg.ollama_uri + "/api/chat",
        json=dict(model=rsokf.config.cfg.chat_model, messages=messages, stream=False),
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


def embed(text):
    """Embed `text` with the configured Ollama embedding model

    Args:
        text (str): text to embed

    Returns:
        list: floats
    """
    r = requests.post(
        rsokf.config.cfg.ollama_uri + "/api/embed",
        json=dict(model=rsokf.config.cfg.embed_model, input=text),
    )
    r.raise_for_status()
    return r.json()["embeddings"][0]
