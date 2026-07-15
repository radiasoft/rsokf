"""Split an OKF bundle's documents into retrievable text chunks.

An OKF (Open Knowledge Format) bundle is a directory tree of markdown
files. Most are "concept" documents: a YAML frontmatter block (``type``,
``title``, ``description``, ...) followed by a markdown body. Two
filenames are reserved and carry no frontmatter: ``index.md`` (a
directory listing) and ``log.md`` (a chronological update history).

See https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkio
import pykern.pkyaml
import re

#: OKF bundles are trees of markdown files
_FILE_RE = re.compile(r"\.md$", re.IGNORECASE)

#: Reserved OKF filenames that carry no frontmatter (SPEC.md sec 3.1)
_RESERVED_BASENAMES = ("index.md", "log.md")

#: Delimits a concept document's YAML frontmatter block (SPEC.md sec 4.1)
_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?\n)---[ \t]*\n?", re.DOTALL)

#: Splits a markdown body on top-level (# or ##) headings
_HEADING_RE = re.compile(r"^#{1,2}[ \t]+(.*)$", re.MULTILINE)


def chunks(okf_dir):
    """Walk `okf_dir` for OKF documents and split each into text chunks

    Args:
        okf_dir (str or py.path.local): root of the OKF bundle

    Returns:
        list: PKDict(path=, heading=, text=, mtime=) in file, then section, order
    """
    d = pykern.pkio.py_path(okf_dir)
    rv = []
    for p in pykern.pkio.walk_tree(d, _FILE_RE):
        rv.extend(_file_chunks(d, p))
    return rv


def _concept_chunks(rel, mtime, text):
    fm, body = _split_frontmatter(text)
    concept_id = rel[: -len(".md")]
    prefix = _concept_prefix(fm)
    rv = [
        PKDict(path=concept_id, heading=heading, text=prefix + t, mtime=mtime)
        for heading, t in _sections(body)
        if t
    ]
    return rv or [
        PKDict(path=concept_id, heading=None, text=prefix.strip(), mtime=mtime)
    ]


def _concept_prefix(frontmatter):
    p = [
        f"{n}: {v}"
        for n, v in (
            ("Title", frontmatter.get("title")),
            ("Type", frontmatter.get("type")),
            ("Description", frontmatter.get("description")),
        )
        if v
    ]
    return ("\n".join(p) + "\n\n") if p else ""


def _file_chunks(okf_dir, path):
    rel = str(okf_dir.bestrelpath(path))
    mtime = path.mtime()
    text = pykern.pkio.read_text(path)
    if path.basename in _RESERVED_BASENAMES:
        return _reserved_chunks(rel, mtime, text)
    return _concept_chunks(rel, mtime, text)


def _reserved_chunks(rel, mtime, text):
    return [
        PKDict(path=rel, heading=heading, text=t, mtime=mtime)
        for heading, t in _sections(text)
        if t
    ]


def _sections(text):
    heading = None
    p = 0
    for h in _HEADING_RE.finditer(text):
        yield heading, text[p : h.start()].strip()
        heading = h.group(1).strip()
        p = h.end()
    yield heading, text[p:].strip()


def _split_frontmatter(text):
    if not (m := _FRONTMATTER_RE.match(text)):
        return PKDict(), text
    return pykern.pkyaml.load_str(m.group(1)) or PKDict(), text[m.end() :]
