# rsokf: `rsokf query` -- answer questions about an OKF repo via Ollama (GitHub issue #1)

## Context

Issue #1 asks for a program that answers questions about an "Open Knowledge
Format" (OKF) repository using a local Ollama server. The issue sketches a
retrieval-augmented pipeline: parse the files, build an embedding index,
retrieve relevant chunks for a question, then ask a local Qwen3 8B model
to answer using that context.

OKF is a real, versioned spec (v0.1):
https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
A bundle is a directory tree of `.md` files. Most are "concept" documents:
a YAML frontmatter block (`type` required; `title`, `description`,
`resource`, `tags`, `timestamp` optional) followed by a markdown body.
Two filenames are reserved and carry no frontmatter: `index.md` (a
directory listing) and `log.md` (a chronological, date-grouped update
history -- see also `~/.claude/memory/tools/okf.md` for the `log.md`
bullet-prefix convention). A concept's "Concept ID" is its path with the
`.md` suffix removed (SPEC.md sec 2).

This is a fresh, nearly-empty pykern-based project (`rsokf/__init__.py`,
`rsokf/rsokf_console.py`, empty `rsokf/pkcli/__init__.py`, one placeholder
import test). The goal of this plan is the first working slice: a single
CLI entry point, `rsokf query "some question"`, that indexes a configured
OKF directory and returns an answer. Interactivity is explicitly deferred.

Decisions confirmed with the user:
- OKF directory is a `pykern.pkconfig` setting (not a CLI arg, not cwd).
- Vector search is pure Python (embeddings stored as blobs in SQLite,
  cosine similarity computed in Python) -- no sqlite-vec/numpy dependency.
- Tests stub the Ollama HTTP client via `monkeypatch.setattr`, matching the
  existing RadiaSoft idiom (e.g. `sirepo/tests/nersc_test.py` stubbing
  `nersc._hpssquota`). Parsing/indexing logic is fully tested without a
  live Ollama server; no test requires Ollama to be running.

## CLI shape

pykern's `pkcli` allows `<project> <module>` (no function name) when the
module has exactly one public function named `default_command` (see
`pykern/pkcli/__init__.py` docstring). So:

- `rsokf/pkcli/query.py` defines `default_command(question)` only.
- Running `rsokf query "what is X"` therefore calls it directly.

## New modules

```
rsokf/
  config.py          pkconfig.init() -- shared runtime config
  ollama_client.py   thin wrapper over Ollama's local HTTP API
  parser.py          walk OKF dir -> list of text chunks
  index.py           SQLite-backed embedding store + cosine search
  pkcli/
    query.py         default_command(question) -- index, retrieve, prompt, answer
```

### `rsokf/config.py`
```python
cfg = pkconfig.init(
    okf_dir=pkconfig.Required(str, "root directory of the OKF bundle to index and query"),
    db=(None, str, "sqlite file for the embedding index (default: <okf_dir>/rsokf.sqlite3)"),
    ollama_uri=("http://localhost:11434", str, "base URL of the local Ollama server"),
    embed_model=("nomic-embed-text", str, "Ollama model used to embed chunks and questions"),
    chat_model=("qwen3:8b", str, "Ollama model used to generate answers"),
    top_k=(5, int, "number of retrieved chunks to include in the answer prompt"),
)
```
Env vars: `RSOKF_CONFIG_OKF_DIR`, `RSOKF_CONFIG_DB`, etc. `okf_dir` has no
sensible default so it is `Required`; `db` defaults to a plain (non-hidden)
file next to the OKF content unless overridden.

### `rsokf/ollama_client.py`
Two small functions using `requests` (already a transitive pykern dep;
will be added to `pyproject.toml` explicitly since it's now a direct
import) against Ollama's native local API (no `openai` package needed):
- `embed(text)` -> `POST {ollama_uri}/api/embed` with `cfg.embed_model`,
  returns `list[float]`.
- `chat(messages)` -> `POST {ollama_uri}/api/chat` with `cfg.chat_model`,
  `stream=False`, returns the reply text.

These are the two functions tests monkeypatch to avoid needing a live
Ollama server.

### `rsokf/parser.py`
`chunks(okf_dir)` walks the directory for `*.md` files (OKF bundles are
all-markdown; there is no separate YAML file type -- YAML only appears
as a concept document's frontmatter block) and yields
`PKDict(path=, heading=, text=, mtime=)`:
- `index.md` / `log.md` (reserved, no frontmatter): body is split on
  top-level `#`/`##` headings via regex; each section is one chunk
  (`heading` = the heading text, e.g. a `log.md` date heading like
  `2026-05-22`).
- Everything else (a concept document): the leading `---`-delimited YAML
  frontmatter is parsed via `pykern.pkyaml.load_str` and the remaining
  body is split on headings the same way. `path` is the Concept ID (`.md`
  stripped). Each section chunk's `text` is prefixed with
  `Title: .../Type: .../Description: ...` (from frontmatter, whichever
  are present) so a chunk is self-explanatory in isolation at retrieval
  time, even without its sibling chunks or frontmatter alongside it.

### `rsokf/index.py`
SQLite table `chunk(path, heading, text, mtime, embedding BLOB)`.
- `ensure_current(okf_dir)`: compare each `parser.chunks()` entry's mtime
  against what's stored; only re-embed (via `ollama_client.embed`) and
  upsert changed/new files, and delete rows for files no longer present.
  Keeps repeated `rsokf query` calls cheap.
- `search(query_embedding, top_k)`: load all stored embeddings, rank by
  cosine similarity computed in plain Python (`sum`/`math.sqrt`, no
  numpy), return the top-k chunk rows.
- Embeddings stored as `array.array('f', values).tobytes()`.

### `rsokf/pkcli/query.py`
`default_command(question)` holds the query logic directly (no separate
`rsokf/query.py` -- it has no other caller, so per the user's direction
the orchestration lives in the CLI module itself):
1. `index.ensure_current(cfg.okf_dir)`
2. `q = ollama_client.embed(question)`
3. `hits = index.search(q, cfg.top_k)`
4. build a prompt: system message instructing the model to answer only
   from the provided context and cite `path`/`heading`; user message with
   the retrieved chunk texts (labeled by source) + the question
5. `return ollama_client.chat(messages)`

pkcli prints the returned string.

## Tests

- `tests/parser_test.py` -- a small OKF-shaped fixture dir
  (`tests/parser_data/`: an `index.md`, a `log.md`, and a `tables/orders.md`
  concept doc with real frontmatter) asserts `parser.chunks()` splits them
  as expected, including the frontmatter-derived prefix and the `.md`-
  stripped Concept ID. No Ollama involved.
- `tests/index_test.py` -- `monkeypatch.setattr(ollama_client, "embed", ...)`
  with a deterministic fake embedding function; verifies `ensure_current`
  populates the db, is idempotent, re-embeds only changed files (touch a
  file, rerun, assert only that row's embedding call fired), and that
  `search` ranks correctly for known fake vectors.
- `tests/pkcli/query_test.py` -- monkeypatches both `ollama_client.embed`
  and `ollama_client.chat`; calls `rsokf.pkcli.query.default_command`
  end-to-end against the fixture dir, asserting it retrieves the expected
  chunks, that the prompt sent to `chat` contains the retrieved context
  and the question, and that the stubbed chat response is returned.
- Delete `tests/import_test.py` per its own docstring ("delete once you
  have real tests").

All new tests follow existing pykern test conventions: run via
`pykern test tests/...`, local imports inside test functions, `pkunit`/
`pkdebug` imports, `PKDict` for structured data, `monkeypatch.setattr`
against the real target functions (pattern confirmed in
`sirepo/tests/nersc_test.py`). Required config (`okf_dir`, and `db` to
point at a scratch file) is forced per test with
`pkconfig.reset_state_for_testing({...})` called before the first import
of `rsokf.config`/`rsokf.index`/etc. in that test, and scratch content
lives under `pkunit.empty_work_dir()` (pattern from
`rsconf/tests/pkcli/build2_test.py`) -- no `conftest.py` needed since
`pykern test` runs each `_test.py` file in its own process.

## Other changes

- `pyproject.toml`: add `requests` to `dependencies` (direct import in
  `ollama_client.py`).
- `README.md` / `docs/index.rst`: leave as-is for this slice; a follow-up
  can document `rsokf query` usage and required env vars once the shape
  settles.

## Explicitly out of scope for this slice

- Interactive/REPL mode (`rsokf query` with no question) -- user said
  "we can make it interactive later."
- A separate `rsokf index` command -- indexing happens transparently
  inside `pkcli.query.default_command()` and is cheap on repeat runs due
  to mtime-based staleness checks.
- sqlite-vec / ANN search.
- Cross-link traversal (SPEC.md sec 5) and citation-graph expansion --
  chunks are retrieved independently by embedding similarity only.
- `okf_version` handling (SPEC.md sec 11) and other soft-conformance
  niceties -- the parser is permissive per SPEC.md sec 9 by construction
  (missing/unknown frontmatter fields are simply omitted from the prefix).

## Verification

- `pykern test` (run from the project root; it auto-discovers everything
  under `tests/`) passes with no Ollama server running (everything
  Ollama-related is stubbed).
- Manual end-to-end check with a real local Ollama server: `brew install
  ollama` if needed, `ollama pull nomic-embed-text && ollama pull
  qwen3:8b`, run `~/brew/opt/ollama/bin/ollama serve`, set
  `RSOKF_CONFIG_OKF_DIR=/path/to/some/okf/repo`, run
  `rsokf query "some question"` and confirm a sensible, cited answer.
- `pykern fmt run .` before committing (formats only RadiaSoft-originated
  `.py` files).
