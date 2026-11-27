"""Server-side limits and session handling. No model calls, no network.

Handlers are called directly with hand-built Requests (httpx / TestClient is
not a dependency).

Run:  .venv/bin/python tests/test_server_limits.py      (also pytest-compatible)
"""

import asyncio
import copy
import json
import os
import sys
import time

import tempfile

os.environ.setdefault("GEMINI_API_KEY", "test-key-not-used")
# never write test traffic into the real prompts.log
os.environ["LOG_FILE_PATH"] = os.path.join(tempfile.mkdtemp(), "prompts.log")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import ratelimit  # noqa: E402
import server  # noqa: E402
from starlette.requests import Request  # noqa: E402

ch = server.ch
server._API_KEY = "test-key-not-used"


def fresh(**limits):
    """Clean in-process state and (optionally) tiny limits for one test."""
    server.SESSIONS.clear()
    server._GREETINGS.clear()
    server._GREETING_LOCKS.clear()
    server._chat_session_min = ratelimit.SlidingWindow(limits.get("smin", 100), 60)
    server._chat_session_hour = ratelimit.SlidingWindow(limits.get("shour", 1000), 3600)
    server._chat_global = ratelimit.SlidingWindow(limits.get("gmin", 1000), 60)
    server._chat_inflight = ratelimit.InFlight(limits.get("inflight", 100))
    server._gate_fail_min = ratelimit.SlidingWindow(limits.get("gate_min", 8), 60)
    server._gate_fail_hour = ratelimit.SlidingWindow(limits.get("gate_hour", 60), 3600)
    server.CHAT_TURN_TIMEOUT = limits.get("timeout", 90)


def session(unlocked=(1,), current=1, sid="sid-a"):
    return {"sid": sid, "auth": True, "unlocked": list(unlocked), "current": current}


def req(sess):
    cookie = f"{server.COOKIE_NAME}={server.encode_session(sess)}".encode()
    return Request({"type": "http", "method": "POST", "path": "/", "query_string": b"",
                    "headers": [(b"cookie", cookie)], "client": ("203.0.113.9", 1),
                    "server": ("t", 80), "scheme": "http"})


def run(coro):
    return asyncio.run(coro)


def body(resp):
    return json.loads(resp.body)


def cookie_session(resp):
    raw = resp.headers["set-cookie"].split(";")[0].split("=", 1)[1]
    return server.decode_session(raw)


def status_of(fn, *a, **k):
    """HTTP status of the HttpError `fn` raises (None if it returns)."""
    try:
        r = fn(*a, **k)
        if asyncio.iscoroutine(r):
            run(r)
    except server.HttpError as e:
        return e.status
    return None


# --------------------------------------------------------------------------- #
# chat budget
# --------------------------------------------------------------------------- #
def test_one_chat_at_a_time_per_session():
    fresh()
    rt = server._check_chat_budget("a")
    assert rt.busy and server._chat_inflight.current == 1
    assert status_of(server._check_chat_budget, "a") == 429        # parallel send refused
    assert server._chat_inflight.current == 1                      # ...without taking a slot
    rt.busy = False
    server._chat_inflight.release()
    assert server._check_chat_budget("a").busy                     # next one is fine


def test_refused_messages_cost_nothing():
    fresh(gmin=1)
    server._check_chat_budget("a").busy = False
    assert status_of(server._check_chat_budget, "b") == 503        # global limit
    assert not server._chat_session_min._hits.get("b")             # not counted against b
    assert not server._chat_session_hour._hits.get("b")
    assert len(server._chat_global._hits[None]) == 1               # only the admitted one
    fresh(inflight=1)
    rt = server._check_chat_budget("a")
    assert status_of(server._check_chat_budget, "b") == 503        # in-flight cap
    assert not server._chat_session_min._hits.get("b") and len(server._chat_global._hits[None]) == 1
    rt.busy = False


def test_session_limits_are_per_session_and_checked_first():
    fresh(smin=2)
    for _ in range(2):
        server._check_chat_budget("a").busy = False
    assert status_of(server._check_chat_budget, "a") == 429
    assert server._check_chat_budget("b")                          # other sessions unaffected
    assert len(server._chat_global._hits[None]) == 3               # the refused one didn't count


def test_hung_model_call_frees_the_slot():
    fresh(timeout=0.2)
    s = session()
    server._send_sync = lambda *a, **k: time.sleep(1.5)            # a model call that hangs
    try:
        assert status_of(server.api_chat, req(s), {"level": 1, "message": "hi"}) == 504
    finally:
        pass
    assert server._chat_inflight.current == 0
    assert server._runtime(s["sid"]).busy is False
    assert not server._runtime(s["sid"]).lock.locked()


# --------------------------------------------------------------------------- #
# cookie / progress race
# --------------------------------------------------------------------------- #
def test_slow_response_cannot_relock_a_circle():
    fresh()
    s = session(unlocked=(1,))                                     # the cookie the chat started with
    server._runtime(s["sid"]).progress.update({1, 2})              # gate unlocked 2 meanwhile
    sent = []

    def fake_send(level, history, message, state=None):
        sent.append(message)
        return "hello", [], history, []

    orig = server._send_sync
    server._send_sync = fake_send
    try:
        resp = run(server.api_chat(req(s), {"level": 1, "message": "hi"}))
    finally:
        server._send_sync = orig
    assert body(resp)["reply"] == "hello"
    assert cookie_session(resp)["unlocked"] == [1, 2]


def test_gate_unlock_is_remembered_server_side():
    fresh()
    s = session()
    right = ch.PASSPHRASES[1]
    resp = run(server.api_passphrase(req(s), {"circle": 1, "passphrase": right}))
    assert body(resp)["ok"] and cookie_session(resp)["unlocked"] == [1, 2]
    assert server._runtime(s["sid"]).progress == {1, 2}
    server._merge_progress(s, server._runtime(s["sid"]))           # a stale request's copy
    assert s["unlocked"] == [1, 2]


# --------------------------------------------------------------------------- #
# Ascent Gate
# --------------------------------------------------------------------------- #
def test_gate_wrong_guesses_are_limited_per_session():
    fresh(gate_min=3)
    s, other = session(), session(sid="sid-b")
    for _ in range(3):
        assert body(run(server.api_passphrase(req(s), {"circle": 1, "passphrase": "WrongGuess"})))["ok"] is False
    assert status_of(server.api_passphrase, req(s), {"circle": 1, "passphrase": "WrongGuess"}) == 429
    assert status_of(server.api_passphrase, req(s), {"circle": 1, "passphrase": ch.PASSPHRASES[1]}) == 429
    # another player is unaffected, and a right answer never counts as a failure
    assert body(run(server.api_passphrase(req(other), {"circle": 1, "passphrase": ch.PASSPHRASES[1]})))["ok"]
    assert not server._gate_fail_min._hits.get("sid-b")


def test_gate_rejects_oversized_input():
    fresh()
    assert status_of(server.api_passphrase, req(session()),
                     {"circle": 1, "passphrase": "x" * (server.MAX_PASSPHRASE_CHARS + 1)}) == 413


# --------------------------------------------------------------------------- #
# vault cap survives a restart
# --------------------------------------------------------------------------- #
def test_restart_does_not_reset_vault_attempts():
    fresh()
    n = ch.circle_number("avaritia")
    s = session(unlocked=range(1, n + 1), current=n)
    for _ in range(3):
        assert body(run(server.api_vault(req(s), {"level": n, "key": "NOT-THE-KEY"})))["ok"] is False
    run(server.api_restart(req(s)))
    rt = server.SESSIONS[s["sid"]]
    assert rt.vault_attempts == {n: 3} and not rt.histories and not rt.progress


# --------------------------------------------------------------------------- #
# greetings
# --------------------------------------------------------------------------- #
class _FakeChat:
    history = []

    def send_message(self, _m):
        pass


def test_greeting_runs_no_tools():
    seen = {}

    class FakeModel:
        def __init__(self, **kw):
            seen.update(kw)

        def start_chat(self, **kw):
            seen["chat_kw"] = kw
            return _FakeChat()

    orig = server.genai.GenerativeModel
    server.genai.GenerativeModel = FakeModel
    try:
        for level in range(1, ch.MAX_PLAYABLE + 1):
            seen.clear()
            server._greet_sync(level)
            assert seen["tools"] is None, level
            assert not seen["chat_kw"].get("enable_automatic_function_calling"), level
    finally:
        server.genai.GenerativeModel = orig


def test_greeting_is_generated_once_per_circle_and_copied():
    fresh()
    calls = []
    Content = server.genai.protos.Content
    Part = server.genai.protos.Part

    def fake_greet(level):
        calls.append(level)
        time.sleep(0.05)                                           # concurrent first loads overlap
        return [Content(role="model", parts=[Part(text="Welcome, traveler.")])]

    orig = server._greet_sync
    server._greet_sync = fake_greet
    try:
        async def many():
            return await asyncio.gather(*[server._greeting_history(1) for _ in range(10)])
        copies = run(many())
        assert calls == [1]                                        # one model call, not ten
        copies[0][0].parts[0].text = "tampered"
        assert copies[1][0].parts[0].text == "Welcome, traveler."  # players never share objects
        s = session()
        for _ in range(3):                                         # load, reset, reload ...
            run(server.api_circle(1, req(s)))
            run(server.api_reset_circle(req(s), {"level": 1}))
        assert calls == [1]
    finally:
        server._greet_sync = orig


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    orig_send = server._send_sync
    for fn in fns:
        server._send_sync = orig_send
        fn()
        print(f"ok  {fn.__name__}")
    print(f"{len(fns)} passed")
