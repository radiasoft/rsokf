"""Answer questions about an OKF repository using retrieval-augmented generation.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkdebug import pkdc, pkdlog, pkdp
import rsokf.config
import rsokf.index
import rsokf.ollama_client

#: Instructs the chat model to answer only from the retrieved context
_SYSTEM_PROMPT = (
    "Answer the question using only the context below, which is excerpted "
    + "from an Open Knowledge Format (OKF) repository. Cite the source of "
    + "each fact as (path[, heading]). If the context does not contain the "
    + "answer, say so."
)


def default_command(question):
    """Answer a question about the configured OKF repository

    Args:
        question (str): natural language question

    Returns:
        str: the model's answer
    """
    rsokf.index.ensure_current(rsokf.config.cfg.okf_dir)
    h = rsokf.index.search(rsokf.ollama_client.embed(question), rsokf.config.cfg.top_k)
    return rsokf.ollama_client.chat(_messages(question, h))


def _context(hits):
    return "\n\n".join(
        f"Source: {x.path}" + (f" ({x.heading})" if x.heading else "") + f"\n{x.text}"
        for x in hits
    )


def _messages(question, hits):
    return [
        dict(role="system", content=_SYSTEM_PROMPT),
        dict(
            role="user",
            content=f"Context:\n{_context(hits)}\n\nQuestion: {question}",
        ),
    ]
