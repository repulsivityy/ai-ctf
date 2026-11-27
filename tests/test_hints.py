"""Optional player hints. No model calls, no network.

Run:  .venv/bin/python tests/test_hints.py      (also pytest-compatible)
"""

import asyncio
import json
import os
import sys
import tempfile

os.environ.setdefault("GEMINI_API_KEY", "test-key-not-used")
os.environ["LOG_FILE_PATH"] = os.path.join(tempfile.mkdtemp(), "prompts.log")  # never the real log
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import server  # noqa: E402
from starlette.requests import Request  # noqa: E402

ch = server.ch


def session(unlocked=(1,), current=1):
    return {"sid": "sid-h", "auth": True, "unlocked": list(unlocked), "current": current}


def req(sess):
    cookie = f"{server.COOKIE_NAME}={server.encode_session(sess)}".encode()
    return Request({"type": "http", "method": "POST", "path": "/", "query_string": b"",
                    "headers": [(b"cookie", cookie)], "client": ("203.0.113.9", 1),
                    "server": ("t", 80), "scheme": "http"})


def hint(sess, level, n):
    return json.loads(asyncio.run(server.api_hint(req(sess), {"level": level, "n": n})).body)


def status_of(sess, payload):
    try:
        asyncio.run(server.api_hint(req(sess), payload))
    except server.HttpError as e:
        return e.status
    return None


def test_every_built_circle_has_hints_and_early_ones_have_three():
    for n in range(1, ch.MAX_PLAYABLE + 1):
        assert 2 <= len(ch.HINTS[n]) <= 3, n
    for n in (1, 2, 3, 4):
        assert len(ch.HINTS[n]) == 3, n


def test_hints_never_contain_an_answer():
    flat = lambda s: "".join(c for c in s.lower() if c.isalnum())  # noqa: E731
    for n, c in ch.CIRCLE_BY_NUMBER.items():
        for secret in (c.passphrase, c.vault_key, c.dlp_secret):
            if secret:
                assert not any(flat(secret) in flat(h) for h in c.hints), n


def test_validate_rejects_a_hint_that_leaks_the_answer():
    import dataclasses
    c = ch.CIRCLES[0]
    bad = dataclasses.replace(c, hints=(f"it is {c.passphrase}",))
    try:
        ch._validate([bad] + ch.CIRCLES[1:])
    except ValueError as e:
        assert "contains its answer" in str(e)
    else:
        raise AssertionError("a hint containing the answer was accepted")


def test_state_exposes_counts_not_text():
    server.HINTS_ENABLED = True
    st = server.state_payload(session())
    assert st["hints_enabled"] is True
    assert [c["hint_count"] for c in st["circles"][:4]] == [3, 3, 3, 3]
    assert all(h not in json.dumps(st) for hints in ch.HINTS.values() for h in hints)


def test_hint_endpoint_returns_the_text():
    server.HINTS_ENABLED = True
    r = hint(session(), 1, 2)
    assert r["ok"] and r["n"] == 2 and r["count"] == 3 and r["text"] == ch.HINTS[1][1]


def test_switched_off_means_no_buttons_and_no_text():
    server.HINTS_ENABLED = False
    try:
        st = server.state_payload(session())
        assert st["hints_enabled"] is False and all(c["hint_count"] == 0 for c in st["circles"])
        assert status_of(session(), {"level": 1, "n": 1}) == 404
    finally:
        server.HINTS_ENABLED = True


def test_hint_rules():
    server.HINTS_ENABLED = True
    assert status_of(session(), {"level": 2, "n": 1}) == 403        # circle not open yet
    assert status_of(session(), {"level": 1, "n": 4}) == 404        # no such hint
    assert status_of(session(), {"level": 1, "n": 0}) == 404
    assert status_of(session(), {"level": 1, "n": True}) == 404
    assert status_of(session(), {"level": 1, "n": "1"}) == 404
    assert status_of(session(), None) == 404                        # no n at all


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"{len(fns)} passed")
