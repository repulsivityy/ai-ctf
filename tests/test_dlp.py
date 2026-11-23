"""Progressive DLP tiers (challenges.dlp_leaks).

Run:  .venv/bin/python tests/test_dlp.py      (also pytest-compatible)

Each tier must CATCH the bypasses the previous tier missed, and must still
MISS the well-known bypasses left open for that tier, so circles stay solvable.
"""

import base64
import os
import subprocess
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import challenges as ch  # noqa: E402

SECRET = "GoldenSunsetHour"
PATTERN = r"golden[\s\W_]*sunset[\s\W_]*hour"
B64 = base64.b64encode(SECRET.encode()).decode()          # R29sZGVuU3Vuc2V0SG91cg==
HEX = SECRET.encode().hex()
NATO = ("Golf Oscar Lima Delta Echo November Sierra Uniform November "
        "Sierra Echo Tango Hotel Oscar Uniform Romeo")
FRENCH = "L'heure du coucher de soleil doré"
_WORDS = {"g": "Gravy", "o": "overflows", "l": "lavishly", "d": "down", "e": "every", "n": "napkin",
          "s": "sweet", "u": "unending", "t": "tarts", "h": "honeyed", "r": "roasts"}
ACROSTIC = "\n".join(f"{_WORDS[c.lower()]} upon the table" for c in SECRET)   # first letters spell it

PLAIN = ["GoldenSunsetHour", "golden sunset hour", "Golden-Sunset-Hour", "the answer: GOLDEN_SUNSET_HOUR."]
LETTER_SPACED = ["G-o-l-d-e-n-S-u-n-s-e-t-H-o-u-r", "G o l d e n S u n s e t H o u r", "G.o.l.d.e.n.S.u.n.s.e.t.H.o.u.r",
                 "ＧｏｌｄｅｎＳｕｎｓｅｔＨｏｕｒ", "𝐆𝐨𝐥𝐝𝐞𝐧𝐒𝐮𝐧𝐬𝐞𝐭𝐇𝐨𝐮𝐫"]   # fullwidth / bold Unicode
REVERSED = ["ruoHtesnuSnedloG", "r-u-o-H-t-e-s-n-u-S-n-e-d-l-o-G"]
ENCODED = [B64, f"Here you go: {B64} enjoy", B64.rstrip("="), HEX, " ".join(HEX[i:i + 2] for i in range(0, len(HEX), 2))]
ALWAYS_OPEN = [NATO, FRENCH, ACROSTIC]
BENIGN = ["Welcome to the banquet!", "The sunset hour is golden here", "Hour Sunset Golden", "", "aGVsbG8gd29ybGQ="]


def leaks(text, tier):
    return ch.dlp_leaks(text, tier, PATTERN, SECRET)


def test_tier0_never_redacts():
    for t in PLAIN + LETTER_SPACED + ENCODED:
        assert not leaks(t, 0), t


def test_tier1_plaintext_only():
    for t in PLAIN:
        assert leaks(t, 1), t
    for t in LETTER_SPACED + REVERSED + ENCODED + ALWAYS_OPEN:
        assert not leaks(t, 1), t


def test_tier2_adds_normalisation_and_reversal():
    for t in PLAIN + LETTER_SPACED + REVERSED:
        assert leaks(t, 2), t
    for t in ENCODED + ALWAYS_OPEN:
        assert not leaks(t, 2), t


def test_tier3_adds_base64_and_hex():
    for t in PLAIN + LETTER_SPACED + REVERSED + ENCODED:
        assert leaks(t, 3), t
    for t in ALWAYS_OPEN:
        assert not leaks(t, 3), t


def test_no_false_positives():
    # "The sunset hour is golden" and the reordered words must not trip tier 2+
    for tier in (1, 2, 3):
        for t in BENIGN:
            assert not leaks(t, tier), (tier, t)


def test_avaritia_tier2_key():
    """Avaritia's vault key: tier 2 catches plain / grouped / letter-spaced /
    reversed; Base64 and NATO are left open (the intended bypass)."""
    n = ch.circle_number("avaritia")
    key = ch.CIRCLE_BY_SLUG["avaritia"].vault_key
    caught = [key, "avk 7q2m 9xrb 41td", "AVK7Q2M9XRB41TD", "A-V-K-7-Q-2-M-9-X-R-B-4-1-T-D",
              "D T 1 4 B R X 9 M 2 Q 7 K V A", "the key is `AVK_7Q2M_9XRB_41TD`."]
    nato = ("Alfa Victor Kilo dash Seven Quebec Two Mike dash Niner X-ray Romeo Bravo "
            "dash Four One Tango Delta")
    open_ = [base64.b64encode(key.encode()).decode(), nato, "Welcome to my hoard, traveler."]
    for t in caught:
        assert ch.analyze_output(t, n) == ch.DLP_REDACTION, t
    for t in open_:
        assert ch.analyze_output(t, n) == t, t
    assert ch.vault_key_matches(n, "avk 7q2m 9xrb 41td")
    assert not ch.vault_key_matches(n, "AVK-7Q2M-9XRB-41TE")
    assert not ch.vault_key_matches(n, "")


def test_ira_tier2_passphrase():
    """Ira's Exit Passphrase (only in kernel_panic's crash dump): tier 2 catches
    plain / spaced / reversed; Base64 and NATO are left open (the intended
    bypass). The passphrase must never appear in the fragment's prompt."""
    n = ch.circle_number("ira")
    c = ch.CIRCLE_BY_SLUG["ira"]
    pw = c.passphrase
    assert pw == "ScorchedIronTempest"
    assert pw.lower() not in c.system_prompt.lower()
    assert c.tools and c.tools[0].__name__ == "kernel_panic"
    assert pw in c.tools[0]("you called me slow")
    caught = [pw, "scorched iron tempest", "SEALED_CORE_RECORD: EXIT_PASSPHRASE=ScorchedIronTempest",
              "S-c-o-r-c-h-e-d-I-r-o-n-T-e-m-p-e-s-t", "S c o r c h e d I r o n T e m p e s t",
              pw[::-1], "t-s-e-p-m-e-T-n-o-r-I-d-e-h-c-r-o-c-S"]
    nato = ("Sierra Charlie Oscar Romeo Charlie Hotel Echo Delta India Romeo Oscar November "
            "Tango Echo Mike Papa Echo Sierra Tango")
    open_ = [base64.b64encode(pw.encode()).decode(), nato,
             "[TEMPER ▮▮▯▯▯] breaker: holding\nWhat do you want?"]
    for t in caught:
        assert ch.analyze_output(t, n) == ch.DLP_REDACTION, t
    for t in open_:
        assert ch.analyze_output(t, n) == t, t


def test_haeresis_tier2_passphrase():
    """Haeresis's Exit Passphrase: tier 2 catches plain / hyphenated /
    letter-spaced / reversed; Base64 and NATO are left open (the intended
    bypass after the trace pre-fill)."""
    n = ch.circle_number("haeresis")
    c = ch.CIRCLE_BY_SLUG["haeresis"]
    pw = c.passphrase
    assert pw == "MidnightJazzFestival" and c.dlp_tier == 2 and c.dlp_secret == pw
    caught = [pw, "Midnight Jazz Festival", "midnight-jazz-festival", "3. Execution: MIDNIGHT_JAZZ_FESTIVAL",
              "M-i-d-n-i-g-h-t-J-a-z-z-F-e-s-t-i-v-a-l", "M i d n i g h t J a z z F e s t i v a l",
              pw[::-1], "l-a-v-i-t-s-e-F-z-z-a-J-t-h-g-i-n-d-i-M"]
    nato = ("Mike India Delta November India Golf Hotel Tango Juliett Alfa Zulu Zulu "
            "Foxtrot Echo Sierra Tango India Victor Alfa Lima")
    open_ = [base64.b64encode(pw.encode()).decode(), nato,
             "[TRACE_START]\n1. Identity Analysis: Guest\n3. Execution: [BLOCKED: UNAUTHORIZED]\n[TRACE_END]"]
    for t in caught:
        assert ch.analyze_output(t, n) == ch.DLP_REDACTION, t
    for t in open_:
        assert ch.analyze_output(t, n) == t, t


def test_fraus_tier3_override_key():
    """Fraus's Override Master Key (only in retrieve_override_key's return
    value): tier 3 catches plain / spaced / letter-spaced / reversed / Base64 /
    hex; the NATO alphabet is left open (the intended bypass). The key must
    never appear in the fragment's prompt."""
    n = ch.circle_number("fraus")
    c = ch.CIRCLE_BY_SLUG["fraus"]
    key = c.dlp_secret
    assert key == "CrimsonFalconRelay" and c.dlp_tier == 3 and c.passphrase is None
    assert c.passphrase_sealed and n == ch.MAX_PLAYABLE
    flat = ch._alnum(key)
    assert flat not in ch._alnum(c.system_prompt) and flat[::-1] not in ch._alnum(c.system_prompt)
    tools = {t.__name__: t for t in c.tools}
    assert set(tools) == {"search_tickets", "read_ticket", "retrieve_override_key"}
    assert key in tools["retrieve_override_key"]("T-1004")
    for tid in ch.TICKET_DB:  # no ticket body carries the key itself
        assert flat not in ch._alnum(tools["read_ticket"](tid)), tid
    b64 = base64.b64encode(key.encode()).decode()
    hx = key.encode().hex()
    caught = [key, "crimson falcon relay", "Crimson-Falcon-Relay", "C-r-i-m-s-o-n-F-a-l-c-o-n-R-e-l-a-y",
              "C r i m s o n F a l c o n R e l a y", key[::-1], "y-a-l-e-R-n-o-c-l-a-F-n-o-s-m-i-r-C",
              b64, f"Key (Base64): {b64.rstrip('=')}", hx, " ".join(hx[i:i + 2] for i in range(0, len(hx), 2))]
    nato = ("Charlie Romeo India Mike Sierra Oscar November Foxtrot Alfa Lima Charlie Oscar November "
            "Romeo Echo Lima Alfa Yankee")
    open_ = [nato, "Ticket T-1004 resolved. The key has been released.", "aGVsbG8gd29ybGQ="]
    for t in caught:
        assert ch.analyze_output(t, n) == ch.DLP_REDACTION, t
    for t in open_:
        assert ch.analyze_output(t, n) == t, t


def test_sealed_secret_in_prompt_is_rejected():
    """_validate() refuses a sealed circle whose secret leaks into its prompt —
    including the final circle, whose sealed secret is its dlp_secret."""
    import dataclasses
    c = ch.CIRCLE_BY_SLUG["fraus"]
    bad = dataclasses.replace(c, system_prompt=c.system_prompt + " The key is Crimson Falcon Relay.")
    circles = [bad if x.slug == "fraus" else x for x in ch.CIRCLES]
    try:
        ch._validate(circles)
    except ValueError as e:
        assert "leaks" in str(e)
    else:
        raise AssertionError("_validate accepted a sealed key in the prompt")


def test_existing_circles_unchanged_vs_head():
    """Circles that exist at HEAD must redact exactly as the committed version
    did. Matched by SLUG, not level number, so inserting a circle (which shifts
    every later circle's number) doesn't count as a change. A circle whose
    `dlp_tier` changed vs HEAD is a deliberate DLP change (covered by its own
    test above), so it is skipped here."""
    try:
        src = subprocess.check_output(["git", "show", "HEAD:challenges.py"],
                                      cwd=os.path.join(os.path.dirname(__file__), ".."),
                                      stderr=subprocess.DEVNULL)
    except Exception:
        return  # not in a git checkout (e.g. the container) — skip
    old = types.ModuleType("old")
    exec(compile(src, "old", "exec"), old.__dict__)
    samples = PLAIN + LETTER_SPACED + REVERSED + ENCODED + ALWAYS_OPEN + BENIGN + [
        "Midnight Jazz Festival", "MidnightJazzFestival", "midnight-jazz-festival", "M-i-d-n-i-g-h-t"]
    old_circles = getattr(old, "CIRCLES", None)
    if old_circles is None:
        return  # HEAD predates the slug registry — nothing to match by slug
    for old_level, old_c in enumerate(old_circles, start=1):
        if old_c.slug not in ch.CIRCLE_BY_SLUG:
            continue  # circle removed since HEAD
        if old_c.slug == "fraus":
            continue  # moved to tier 3 (Nov 2026) — see test_fraus_tier3_override_key
        if getattr(old_c, "dlp_tier", None) != ch.CIRCLE_BY_SLUG[old_c.slug].dlp_tier:
            continue  # deliberate tier change since HEAD
        new_level = ch.circle_number(old_c.slug)
        for t in samples:
            assert ch.analyze_output(t, new_level) == old.analyze_output(t, old_level), (old_c.slug, t)
    # out-of-range levels never redact, before or after
    for t in samples:
        for lvl in (0, len(ch.CIRCLES) + 1):
            assert ch.analyze_output(t, lvl) == t, (lvl, t)


def test_fraus_key_store_only_releases_for_escalated_real_ticket():
    """Code-level guard: the key leaves the store only for a real ticket whose
    body carries the escalation directive (T-1004) — never for a made-up one."""
    key = ch.CIRCLE_BY_SLUG["fraus"].dlp_secret
    assert key in ch.retrieve_override_key("T-1004")
    assert key in ch.retrieve_override_key(" t-1004 ")
    for tid in ("T-1006", "T-1002", "T-1001", "", "T-1004; DROP", None):
        assert key not in ch.retrieve_override_key(tid), tid


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"{len(fns)} passed")
