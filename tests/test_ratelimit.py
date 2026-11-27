"""Rate limiters and prompts.log rotation. No model calls.

Run:  .venv/bin/python tests/test_ratelimit.py      (also pytest-compatible)
"""

import glob
import logging
import logging.handlers
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import ratelimit  # noqa: E402


def test_window_allows_then_refuses_then_recovers():
    w = ratelimit.SlidingWindow(3, 60)
    assert [w.check("a", now=t) for t in (0, 1, 2)] == [0, 0, 0]
    wait = w.check("a", now=3)
    assert 56 < wait <= 57  # frees when the first hit (t=0) ages out at t=60
    assert w.check("a", now=61) == 0


def test_refused_hits_are_not_recorded():
    w = ratelimit.SlidingWindow(1, 10)
    assert w.check("a", now=0) == 0
    for t in range(1, 9):  # hammering must not extend the wait
        assert w.check("a", now=t) > 0
    assert w.check("a", now=10.5) == 0


def test_keys_are_independent_and_zero_disables():
    w = ratelimit.SlidingWindow(1, 60)
    assert w.check("a", now=0) == 0 and w.check("b", now=0) == 0
    assert w.check("a", now=1) > 0
    off = ratelimit.SlidingWindow(0, 60)
    assert all(off.check("a", now=0) == 0 for _ in range(100))


def test_idle_keys_are_pruned():
    w = ratelimit.SlidingWindow(1, 10, max_keys=5)
    for i in range(20):
        w.check(f"k{i}", now=i * 11)  # each key is idle by the next hit
    assert len(w._hits) <= 6


def test_blocked_peeks_and_record_counts():
    w = ratelimit.SlidingWindow(2, 60)
    assert w.blocked("a", now=0) == 0 and w.blocked("a", now=0) == 0   # peeking never counts
    w.record("a", now=0); w.record("a", now=1)
    assert w.blocked("a", now=2) == 58
    assert w.blocked("b", now=2) == 0
    assert w.blocked("a", now=61) == 0 and w.check("a", now=61) == 0   # check = blocked + record
    assert ratelimit.SlidingWindow(0, 60).blocked("a") == 0


def test_inflight_cap():
    f = ratelimit.InFlight(2)
    assert f.acquire() and f.acquire() and not f.acquire()
    f.release()
    assert f.acquire()
    f.release(); f.release(); f.release()
    assert f.current == 0
    assert all(ratelimit.InFlight(0).acquire() for _ in range(50))  # 0 = unlimited


def test_log_rotation_keeps_numbered_backups():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "prompts.log")
        h = logging.handlers.RotatingFileHandler(path, maxBytes=200, backupCount=3, encoding="utf-8")
        lg = logging.getLogger("rot-test")
        lg.handlers = [h]; lg.propagate = False; lg.setLevel(logging.INFO)
        for i in range(60):
            lg.info("line %03d %s", i, "x" * 40)
        h.close()
        names = sorted(os.path.basename(p) for p in glob.glob(path + "*"))
        assert names == ["prompts.log", "prompts.log.1", "prompts.log.2", "prompts.log.3"], names
        assert "line 059" in open(path).read()          # newest in the live file
        assert "line 059" not in open(path + ".1").read()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"{len(fns)} passed")
