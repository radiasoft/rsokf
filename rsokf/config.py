"""Runtime configuration for :mod:`rsokf`.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkconfig

cfg = pykern.pkconfig.init(
    chat_model=("qwen3:8b", str, "Ollama model used to generate answers"),
    db=(
        None,
        str,
        "sqlite file for the embedding index (default: <okf_dir>/rsokf.sqlite3)",
    ),
    embed_model=(
        "nomic-embed-text",
        str,
        "Ollama model used to embed chunks and questions",
    ),
    okf_dir=pykern.pkconfig.Required(
        str, "root directory of the OKF bundle to index and query"
    ),
    ollama_uri=("http://localhost:11434", str, "base URL of the local Ollama server"),
    top_k=(5, int, "number of retrieved chunks to include in the answer prompt"),
)
