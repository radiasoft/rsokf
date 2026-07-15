"""SQLite-backed embedding index for an OKF repository.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import array
import contextlib
import math
import pykern.pkio
import rsokf.config
import rsokf.ollama_client
import rsokf.parser
import sqlite3

#: array.array typecode used to pack/unpack embeddings into a BLOB column
_EMBEDDING_TYPE = "f"


def ensure_current(okf_dir):
    """Bring the embedding index up to date with the files in `okf_dir`

    Only chunks whose file mtime changed since the last index are re-embedded;
    chunks for files/headings no longer present are removed.

    Args:
        okf_dir (str or py.path.local): directory containing the OKF repo
    """
    c = rsokf.parser.chunks(okf_dir)
    with contextlib.closing(_connect()) as conn:
        s = _stored_mtimes(conn)
        for x in c:
            if s.get((x.path, x.heading)) != x.mtime:
                _upsert(conn, x, rsokf.ollama_client.embed(x.text))
        _delete_stale(conn, {(x.path, x.heading) for x in c})
        conn.commit()


def search(query_embedding, top_k):
    """Return the `top_k` indexed chunks most similar to `query_embedding`

    Args:
        query_embedding (list): floats
        top_k (int): number of chunks to return

    Returns:
        list: PKDict(path=, heading=, text=, similarity=) ranked most similar first
    """
    with contextlib.closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT path, heading, text, embedding FROM chunk"
        ).fetchall()
    return _rank(rows, query_embedding, top_k)


def _connect():
    conn = sqlite3.connect(str(_db_path()))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunk ("
        + "path TEXT NOT NULL, "
        + "heading TEXT, "
        + "text TEXT NOT NULL, "
        + "mtime REAL NOT NULL, "
        + "embedding BLOB NOT NULL)"
    )
    return conn


def _cosine(a, b):
    d = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / d if d else 0.0


def _db_path():
    if rsokf.config.cfg.db:
        return pykern.pkio.py_path(rsokf.config.cfg.db)
    return pykern.pkio.py_path(rsokf.config.cfg.okf_dir).join("rsokf.sqlite3")


def _delete_stale(conn, current_keys):
    for path, heading in set(_stored_mtimes(conn).keys()) - current_keys:
        conn.execute(
            "DELETE FROM chunk WHERE path = ? AND heading IS ?", (path, heading)
        )


def _pack(values):
    return array.array(_EMBEDDING_TYPE, values).tobytes()


def _rank(rows, query_embedding, top_k):
    r = sorted(
        (
            PKDict(
                path=path,
                heading=heading,
                text=text,
                similarity=_cosine(query_embedding, _unpack(embedding)),
            )
            for path, heading, text, embedding in rows
        ),
        key=lambda x: x.similarity,
        reverse=True,
    )
    return r[:top_k]


def _stored_mtimes(conn):
    return {
        (path, heading): mtime
        for path, heading, mtime in conn.execute(
            "SELECT path, heading, mtime FROM chunk"
        )
    }


def _unpack(blob):
    return array.array(_EMBEDDING_TYPE, blob).tolist()


def _upsert(conn, chunk, embedding):
    conn.execute(
        "DELETE FROM chunk WHERE path = ? AND heading IS ?", (chunk.path, chunk.heading)
    )
    conn.execute(
        "INSERT INTO chunk (path, heading, text, mtime, embedding) VALUES (?, ?, ?, ?, ?)",
        (chunk.path, chunk.heading, chunk.text, chunk.mtime, _pack(embedding)),
    )
