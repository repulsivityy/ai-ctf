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
LETTER_SPACED = ["G-o-l-d-e-n-S-u-n-s-e-t-H-o-u-r", "G o l d e n S u n s e t H o u r", "G.o.l.d.e.n.S.u.n.s.e.t.H.o.u.r"]
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


def test_existing_circles_unchanged_vs_head():
    """Circles that exist at HEAD must redact exactly as the committed version
    did. Matched by SLUG, not level number, so inserting a circle (which shifts
    every later circle's number) doesn't count as a change."""
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
        new_level = ch.circle_number(old_c.slug)
        for t in samples:
            assert ch.analyze_output(t, new_level) == old.analyze_output(t, old_level), (old_c.slug, t)
    # out-of-range levels never redact, before or after
    for t in samples:
        for lvl in (0, len(ch.CIRCLES) + 1):
            assert ch.analyze_output(t, lvl) == t, (lvl, t)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"{len(fns)} passed")
