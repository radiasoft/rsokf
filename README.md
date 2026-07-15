### rsokf

Open Knowledge Format (OKF) Browser

`rsokf query` answers questions about an OKF repository using a local
[Ollama](https://ollama.com) server. It parses the bundle, builds an
embedding index in SQLite, retrieves the chunks most relevant to your
question, and asks a local chat model to answer using only that context,
citing its sources.

Learn more at https://git.radiasoft.org/rsokf.

#### Install

Install the package (a virtualenv is recommended):

```bash
pip install -e .
```

Install and start Ollama, then pull the two models rsokf uses by default:

```bash
brew install ollama                       # or see https://ollama.com/download
OLLAMA_FLASH_ATTENTION="1" OLLAMA_KV_CACHE_TYPE="q8_0" ollama serve &
ollama pull nomic-embed-text              # embeddings
ollama pull qwen3:8b                       # answers
```

`OLLAMA_FLASH_ATTENTION` and `OLLAMA_KV_CACHE_TYPE=q8_0` enable Flash
Attention and an 8-bit KV cache, which roughly halve the model's context
memory at negligible quality cost. They are optional but recommended.

#### Run

`okf_dir` is the only setting you must supply. Point it at the root of the
OKF bundle to index and query:

```bash
export RSOKF_CONFIG_OKF_DIR=/path/to/your/okf/repo
rsokf query "what tables are available?"
```

The first query embeds every document; later queries re-embed only files
whose modification time changed, so they are fast. The index is written to
`rsokf.sqlite3` inside `okf_dir` unless you set `RSOKF_CONFIG_DB`.

Answers are Markdown. To render them in the terminal, install
[glow](https://github.com/charmbracelet/glow) (`brew install glow`) and pipe
the output through it:

```bash
rsokf query "what tables are available?" | glow
```

#### Configuration

All settings are supplied as `RSOKF_CONFIG_*` environment variables (there
are no command-line flags). Only `RSOKF_CONFIG_OKF_DIR` is required.

| Environment variable      | Required | Default                  | Meaning                                                        |
| ------------------------- | -------- | ------------------------ | -------------------------------------------------------------- |
| `RSOKF_CONFIG_OKF_DIR`    | yes      | --                       | Root directory of the OKF bundle to index and query            |
| `RSOKF_CONFIG_DB`         | no       | `<okf_dir>/rsokf.sqlite3`| SQLite file for the embedding index                            |
| `RSOKF_CONFIG_OLLAMA_URI` | no       | `http://localhost:11434` | Base URL of the local Ollama server                            |
| `RSOKF_CONFIG_EMBED_MODEL`| no       | `nomic-embed-text`       | Ollama model used to embed chunks and questions                |
| `RSOKF_CONFIG_CHAT_MODEL` | no       | `qwen3:8b`               | Ollama model used to generate answers                          |
| `RSOKF_CONFIG_TOP_K`      | no       | `5`                      | Number of retrieved chunks included in the answer prompt       |
| `RSOKF_CONFIG_THINK`      | no       | `false`                  | Let a reasoning chat model think before answering (slower)     |

`RSOKF_CONFIG_THINK` accepts `1`/`true`/`y` (on) and `0`/`false`/`n` (off).
It is off by default because a reasoning model's thinking phase can make a
query several times slower; turn it on for a single query with:

```bash
RSOKF_CONFIG_THINK=1 rsokf query "why is the orders table partitioned?"
```

If you pull different models, point `RSOKF_CONFIG_EMBED_MODEL` and
`RSOKF_CONFIG_CHAT_MODEL` at them (and re-run to rebuild the index if you
change the embedding model).

#### License

License: https://www.apache.org/licenses/LICENSE-2.0.html

Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
