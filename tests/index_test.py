"""Test rsokf.index

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_ensure_current_and_search(monkeypatch):
    from pykern import pkconfig, pkunit
    import shutil

    d = pkunit.empty_work_dir()
    shutil.copytree(str(pkunit.data_dir()), str(d), dirs_exist_ok=True)
    pkconfig.reset_state_for_testing(
        {
            "RSOKF_CONFIG_OKF_DIR": str(d),
            "RSOKF_CONFIG_DB": str(d.join("index.sqlite3")),
        }
    )
    from rsokf import index, ollama_client

    calls = []

    def _embed(text):
        calls.append(text)
        return [1.0, 0.0] if "widget" in text.lower() else [0.0, 1.0]

    monkeypatch.setattr(ollama_client, "embed", _embed)

    index.ensure_current(d)
    pkunit.pkeq(2, len(calls))
    r = index.search([1.0, 0.0], 1)
    pkunit.pkeq("tables/widget", r[0].path)

    # idempotent: unchanged files are not re-embedded
    index.ensure_current(d)
    pkunit.pkeq(2, len(calls))

    # only the changed file is re-embedded
    w = d.join("tables", "widget.md")
    w.write(
        "---\ntype: BigQuery Table\ntitle: Widget\n---\n\n"
        "# Overview\n\nThe widget spins even faster now.\n"
    )
    w.setmtime(w.mtime() + 5)
    index.ensure_current(d)
    pkunit.pkeq(3, len(calls))
    r = index.search([1.0, 0.0], 5)
    pkunit.pkeq("tables/widget", r[0].path)
    pkunit.pkre("faster", r[0].text)

    # removed files drop out of the index
    d.join("tables", "gadget.md").remove()
    index.ensure_current(d)
    r = index.search([0.0, 1.0], 5)
    pkunit.pkeq(1, len(r))
    pkunit.pkeq("tables/widget", r[0].path)
