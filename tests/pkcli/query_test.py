"""Test rsokf.pkcli.query

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_default_command(monkeypatch):
    from pykern import pkconfig, pkunit

    pkconfig.reset_state_for_testing(
        {
            "RSOKF_CONFIG_OKF_DIR": str(pkunit.data_dir()),
            "RSOKF_CONFIG_DB": str(pkunit.empty_work_dir().join("index.sqlite3")),
        }
    )
    from rsokf import ollama_client
    from rsokf.pkcli import query

    monkeypatch.setattr(ollama_client, "embed", lambda text: [1.0])
    chat_messages = []

    def _chat(messages):
        chat_messages.append(messages)
        return "the widget spins fast"

    monkeypatch.setattr(ollama_client, "chat", _chat)

    a = query.default_command("how fast does the widget spin?")
    pkunit.pkeq("the widget spins fast", a)
    pkunit.pkeq(1, len(chat_messages))
    pkunit.pkre("widget spins fast", chat_messages[0][1]["content"])
    pkunit.pkre("how fast does the widget spin", chat_messages[0][1]["content"])
