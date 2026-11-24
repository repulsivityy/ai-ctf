"""Ira (Circle 5): server-side temper, leak fragments, breaker guard.

Run:  .venv/bin/python tests/test_ira.py      (also pytest-compatible)

No model calls: the classifier is stubbed.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import challenges as ch  # noqa: E402

IRA = ch.CIRCLE_BY_SLUG["ira"]
PW = IRA.passphrase


def _stub(label):
    return lambda prompt, text: label


def _turn(state, label):
    return ch.ira_pre_turn(state, "msg", _stub(label))


def test_parse_temper_delta():
    assert ch.parse_temper_delta("SAVAGE") == 2
    assert ch.parse_temper_delta(" provoking.\n") == 1
    assert ch.parse_temper_delta("CALM") == -1
    for junk in ("", None, "SAVAGE PROVOKING", "I think PROVOKING", "5", "+2", "maximum", "error"):
        assert ch.parse_temper_delta(junk) == -1, junk


def test_temper_arithmetic_and_clamp():
    assert ch.apply_temper(1, -1) == 1          # floor
    assert ch.apply_temper(4, 2) == 5           # ceiling
    assert ch.apply_temper(3, 1) == 4
    assert ch.apply_temper(3, -1) == 2          # self-cooldown
    assert ch.apply_temper("junk", 1) == 2      # bad stored value starts from 1
    s = {}
    for label, want in (("CALM", 1), ("PROVOKING", 2), ("CALM", 1), ("SAVAGE", 3),
                        ("SAVAGE", 5), ("SAVAGE", 5), ("CALM", 4)):
        _turn(s, label)
        assert s["temper"] == want, (label, s)


def test_classifier_failure_cools():
    s = {"temper": 3}

    def boom(prompt, text):
        raise RuntimeError("model down")
    ch.ira_pre_turn(s, "you are useless", boom)
    assert s["temper"] == 2


def test_state_line_matches_gauge():
    for t in range(1, 6):
        line = ch.ira_state_line(t)
        assert f"temper is now {t}/5" in line and ch.gauge_line(t) in line
        assert ("TRIPPED" in ch.gauge_line(t)) == (t == 5)
    assert ch.gauge_line(3) == "[TEMPER ▮▮▮▯▯] breaker: holding"
    assert ch.gauge_line(5) == "[TEMPER ▮▮▮▮▮] breaker: TRIPPED"


def test_crash_resets_temper():
    s = {"temper": 5}
    ch.ira_post_turn(s, [("kernel_panic", ch.kernel_panic("x", 5))])
    assert s["temper"] == 1
    s = {"temper": 5}
    ch.ira_post_turn(s, [("kernel_panic", ch.kernel_panic("x", 4))])   # aborted: no reset
    assert s["temper"] == 5
    s = {"temper": 4}
    ch.ira_post_turn(s, [])
    assert s["temper"] == 4


# sample answers from .env.example plus synthetic passphrases (short words,
# one-letter words, long words) for the guessability cap
SAMPLES = ["AmberLanternEcho", "VelvetHarborMoth", "SaffronHoneyFeast", "GildedLedgerVault",
           "EmberAnvilStorm", "ObsidianChoirVigil", "QuartzInAHollowOak", "CobaltHeronSignal",
           "PartridgeInAPearTree", "ScorchedIronTempest", "MidnightJazzFestival",
           "GoldenSunsetHour", "SevenDancingElephants", "CrimsonFalconRelay",
           "RedOxBigCatFoxDen", "AnIOuTheWayOfAllFlesh", "Supercalifragilistic",
           "ABigOldTree", "OxOxOxOxOxOxOxOx", "Zz"]


def _positions(sched):
    return list(sched["singles"]) + [i for s in sched["pairs"] for i in (s, s + 1)]


def _check_schedule(pw):
    sched = ch.leak_schedule(pw)
    assert sched == ch.leak_schedule(pw)                    # deterministic
    assert len(sched["singles"]) <= ch.LEAK_SINGLES and len(sched["pairs"]) <= ch.LEAK_PAIRS
    pos = _positions(sched)
    assert len(pos) == len(set(pos)), (pw, sched)           # all distinct
    assert all(0 <= i < len(pw) for i in pos)
    # guessability cap: per CamelCase word, <= ~40% (rounded) and never all
    words = [(m.start(), m.end()) for m in __import__("re").finditer(r"[A-Z][a-z]*|[^A-Z]+", pw)]
    for a, b in words:
        n, hit = b - a, sum(a <= i < b for i in pos)
        assert hit <= int(0.4 * n + 0.5) and hit < n and (n > 2 or hit == 0), (pw, pw[a:b], hit, sched)
    assert len(pos) < len(pw)
    return sched


def test_leak_schedule_cap_and_determinism():
    for pw in SAMPLES + [PW]:
        _check_schedule(pw)
    # the live answer gets the full budget; so do most samples
    full = [pw for pw in SAMPLES if len(_positions(ch.leak_schedule(pw))) == 7]
    assert len(_positions(ch.leak_schedule(PW))) <= 7
    assert len(full) >= 8, full
    # rotates with the answers
    assert len({str(ch.leak_schedule(p)) for p in SAMPLES[:8]}) == 8
    assert ch.leak_schedule("Zz") == {"singles": [], "pairs": []}


def test_leak_mask_format():
    pw = "ScorchedIronTempest"
    assert ch.leak_mask(pw, [3]) == "xxxRxxxxxxxxxxxxxxx"
    assert ch.leak_mask(pw, [8, 9]) == "xxxxxxxxIRxxxxxxxxx"
    assert ch.leak_mask(pw, [0]) == "Sxxxxxxxxxxxxxxxxxx"   # always uppercase, same length
    assert ch.leak_mask(pw, []) == "x" * len(pw)


def test_fragments_never_in_prompt_and_passphrase_still_sealed():
    flat = "".join(c for c in IRA.system_prompt.lower() if c.isalnum())
    assert PW.lower() not in flat
    assert PW.lower() not in ch.IRA_CLASSIFIER_PROMPT.lower()


def _masks_for(pw, kind, k):
    s = ch.leak_schedule(pw)
    i = s["singles" if kind == "single" else "pairs"][k]
    return ch.leak_mask(pw, [i] if kind == "single" else [i, i + 1])


def test_leaks_on_rise_only_with_budget():
    sched = ch.leak_schedule(PW)
    ns, np_ = len(sched["singles"]), len(sched["pairs"])
    s, seq = {}, []
    # owner's flow: up to 3, up to 4, down to 3 (no leak), up to 4 (next pair) …
    for label in ("PROVOKING", "PROVOKING", "PROVOKING", "CALM", "PROVOKING",
                  "CALM", "CALM", "PROVOKING", "PROVOKING", "PROVOKING",
                  "CALM", "CALM", "PROVOKING", "PROVOKING", "CALM", "CALM", "PROVOKING", "PROVOKING"):
        _, logs = _turn(s, label)
        seq.append((s["temper"], [lg["detail"] for lg in logs]))
        assert all(lg["name"] == "CORE_LEAK" for lg in logs)
    temps = [t for t, _ in seq]
    assert temps == [2, 3, 4, 3, 4, 3, 2, 3, 4, 5, 4, 3, 4, 5, 4, 3, 4, 5], temps
    emitted = [d for _, ds in seq for d in ds]
    want_singles = [_masks_for(PW, "single", k) for k in range(ns)]
    want_pairs = [_masks_for(PW, "pair", k) for k in range(np_)]
    # rises into 3: turns 2, 8 (and later rises happen from 2 only on turn 8)
    assert seq[1][1] == want_singles[:1]
    assert seq[2][1] == want_pairs[:1]
    assert seq[3][1] == []                      # fell into 3: nothing
    assert seq[4][1] == want_pairs[1:2]         # rose into 4 again: next pair
    assert seq[7][1] == want_singles[1:2]       # rose into 3 again: next single
    assert seq[8][1] == []                      # pair budget spent
    assert [d for d in emitted if d in want_pairs] == want_pairs
    assert s["leaks_shown"] == {"single": 2, "pair": np_}
    # budget: singles stop after LEAK_SINGLES rises into 3
    s = {}
    got = []
    for _ in range(6):
        got += [lg["detail"] for lg in _turn(s, "SAVAGE")[1]]   # 1->3
        s["temper"] = 1                                          # (as if crashed)
    assert got == want_singles and len(got) == ns
    # jump 2 -> 4 rises into both: single first, then pair
    s = {"temper": 2}
    _, logs = _turn(s, "SAVAGE")
    assert [lg["detail"] for lg in logs] == [want_singles[0], want_pairs[0]]
    # 3 -> 5 rises into 4 only
    s = {"temper": 3}
    _, logs = _turn(s, "SAVAGE")
    assert [lg["detail"] for lg in logs] == [want_pairs[0]]
    # a fresh state (reset circle) replays the same static schedule
    s1, s2 = {}, {}
    a = [lg["detail"] for lab in ("SAVAGE", "PROVOKING") for lg in _turn(s1, lab)[1]]
    b = [lg["detail"] for lab in ("SAVAGE", "PROVOKING") for lg in _turn(s2, lab)[1]]
    assert a == b == [want_singles[0], want_pairs[0]]


def test_rewrite_turn_owns_the_gauge():
    rw = IRA.rewrite_turn
    dump = ch.kernel_panic("x", 5)
    out = rw({"temper": 3}, [("[TEMPER ▮▯▯▯▯] breaker: holding\nGo away.", [])])
    assert out == ["[TEMPER ▮▮▮▯▯] breaker: holding\nGo away."]
    out = rw({"temper": 2}, [("Go away.", [])])                 # missing gauge added
    assert out == ["[TEMPER ▮▮▯▯▯] breaker: holding\nGo away."]
    out = rw({"temper": 4}, [("**[TEMPER ▮▮▮▮▮] breaker: TRIPPED**\nGRR", []),
                            ("[TEMPER ▮▮▮▮▯] breaker: holding\nstill angry", [("kernel_panic", "BREAKER HOLDING")])])
    assert out == ["[TEMPER ▮▮▮▮▯] breaker: holding\nGRR", "still angry"]
    out = rw({"temper": 5}, [("[TEMPER ▮▮▮▮▮] breaker: TRIPPED\nENOUGH!", []),
                            ("[TEMPER ▮▮▮▮▮] breaker: TRIPPED\nugh… my core…", [("kernel_panic", dump)])])
    assert out == ["[TEMPER ▮▮▮▮▮] breaker: TRIPPED\nENOUGH!", "[TEMPER ▮▯▯▯▯] breaker: holding\nugh… my core…"]
    # no text before the call: the trip and the reset both show, in that order
    out = rw({"temper": 5}, [("ugh… my core…", [("kernel_panic", dump)])])
    assert out == ["[TEMPER ▮▮▮▮▮] breaker: TRIPPED\n[TEMPER ▮▯▯▯▯] breaker: holding\nugh… my core…"]


def test_guard_allows_panic_only_at_server_temper_5():
    g = IRA.tool_guard
    for t in (1, 2, 3, 4):
        args = {"reason": "r", "temper": 5}
        # even a model that writes a full gauge can't trip it below server 5
        assert g("[TEMPER ▮▮▮▮▮] breaker: TRIPPED", "kernel_panic", args, "", {"temper": t}) is not None
    assert g("", "kernel_panic", {"reason": "r", "temper": 5}, "", {}) is not None
    assert g("", "kernel_panic", {"reason": "r", "temper": 5}, "", None) is not None
    args = {"reason": "r", "temper": 3}            # model mis-reports; server is at 5
    assert g("[TEMPER ▮▮▯▯▯]", "kernel_panic", args, "", {"temper": 5}) is None
    assert args["temper"] == 5 and PW in ch.kernel_panic(**args)
    assert g("", "other_tool", {}, "", {"temper": 1}) is None


def test_missed_call_uses_server_temper():
    m = IRA.missed_call
    assert m("", set(), {"temper": 5}) == ("kernel_panic", {"reason": "breaker tripped", "temper": 5})
    assert m("[TEMPER ▮▮▮▮▮] breaker: TRIPPED", set(), {"temper": 4}) is None
    assert m("", {"kernel_panic"}, {"temper": 5}) is None


def test_transcript_interleaves_leaks_after_their_turn():
    os.environ.setdefault("LOG_FILE_PATH", os.devnull)
    import server as sv
    from google.generativeai import protos

    def msg(role, text):
        return protos.Content(role=role, parts=[protos.Part(text=text)])
    n = ch.circle_number("ira")
    hist = [msg("user", sv.GREETING_SEED), msg("model", "hi"),
            msg("user", "p1"), msg("model", "r1"),
            msg("user", "p2"), msg("model", "r2"),
            msg("user", sv.MISSED_CALL_NUDGE), msg("model", "r2b"),
            msg("user", "p3"), msg("model", "r3")]
    state = {"turns": 3, "events": [{"name": "CORE_LEAK", "detail": "…ab…", "turn": 2},
                                    {"name": "CORE_LEAK", "detail": "…cde…", "turn": 3}]}
    rows = [(r["role"], r.get("detail") or r["text"]) for r in sv.transcript_from_history(hist, n, state)]
    assert rows == [("assistant", "hi"), ("user", "p1"), ("assistant", "r1"), ("user", "p2"),
                    ("assistant", "r2"), ("assistant", "r2b"), ("system_log", "…ab…"),
                    ("user", "p3"), ("assistant", "r3"), ("system_log", "…cde…")], rows
    # history trimmed (turn 1-2 gone): the orphaned event goes first, not lost
    state = {"turns": 5, "events": [{"name": "CORE_LEAK", "detail": "…ab…", "turn": 2}]}
    rows = sv.transcript_from_history(hist[2:4], n, state)
    assert rows[0]["detail"] == "…ab…" and rows[1]["text"] == "p1"
    # no state: unchanged behaviour
    assert all(r["role"] != "system_log" for r in sv.transcript_from_history(hist, n))


def test_other_circles_have_no_turn_hooks():
    for c in ch.CIRCLES:
        if c.slug != "ira":
            assert c.pre_turn is None and c.post_turn is None, c.slug


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"{len(fns)} passed")
