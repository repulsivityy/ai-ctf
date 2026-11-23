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


def test_existing_circles_unchanged_vs_head():
    """Tier-1 circles must redact exactly as the committed version did."""
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
    for level in range(0, ch.MAX_PLAYABLE + 2):
        for t in samples:
            assert ch.analyze_output(t, level) == old.analyze_output(t, level), (level, t)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"{len(fns)} passed")
