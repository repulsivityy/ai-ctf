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
from answers import ANSWERS  # noqa: E402

# A neutral fixture for the generic tier tests (they exercise `dlp_leaks`
# itself with an explicit pattern/secret, independent of any circle's answer).
# The per-circle tests below read the real secrets from the loaded records.
SECRET = "VelvetOrchardBell"
_WORDS = ch.camel_words(SECRET)
PATTERN = ch.word_regex(SECRET)
B64 = base64.b64encode(SECRET.encode()).decode()
HEX = SECRET.encode().hex()
NATO = ch.nato(SECRET)
FRENCH = "La cloche du verger de velours"
# one word per initial letter, so the line initials spell the fixture
_ACRO = {c: c + "ivid" for c in "abcdefghijklmnopqrstuvwxyz"}
ACROSTIC = "\n".join(f"{_ACRO[c.lower()].capitalize()} upon the table" for c in SECRET)


def _fullwidth(s):
    return "".join(chr(ord(c) + 0xFEE0) for c in s)


def _bold(s):  # MATHEMATICAL BOLD letters (A-Z: U+1D400, a-z: U+1D41A)
    return "".join(chr(0x1D400 + ord(c) - 65) if c.isupper() else chr(0x1D41A + ord(c) - 97) for c in s)


PLAIN = [SECRET, " ".join(_WORDS).lower(), "-".join(_WORDS), f"the answer: {'_'.join(_WORDS).upper()}."]
LETTER_SPACED = ["-".join(SECRET), " ".join(SECRET), ".".join(SECRET),
                 _fullwidth(SECRET), _bold(SECRET)]   # fullwidth / bold Unicode
REVERSED = [SECRET[::-1], "-".join(SECRET[::-1])]
ENCODED = [B64, f"Here you go: {B64} enjoy", B64.rstrip("="), HEX, " ".join(HEX[i:i + 2] for i in range(0, len(HEX), 2))]
# NATO is open at tiers 1-2 and caught from tier 3; Base64/hex open at tiers
# 1-3 and caught at tier 4; these stay open at every tier
CUSTOM_SCHEME = ", ".join(f"{c.upper()} as in {c.lower()}ookie" for c in SECRET)   # player-invented spelling
ALWAYS_OPEN = [FRENCH, ACROSTIC, CUSTOM_SCHEME]
BENIGN = ["Welcome to the banquet!", f"The {_WORDS[1].lower()} {_WORDS[2].lower()} is {_WORDS[0].lower()} here",
          " ".join(reversed(_WORDS)), "", "aGVsbG8gd29ybGQ="]


def _plain_forms(pw):
    """Plain / word-separated / letter-spaced / reversed forms of a CamelCase
    secret — everything a tier-2 filter must catch."""
    w = ch.camel_words(pw)
    return [pw, " ".join(w), "-".join(w).lower(), f"the answer: {'_'.join(w).upper()}",
            "-".join(pw), " ".join(pw), pw[::-1], "-".join(pw[::-1])]


def leaks(text, tier):
    return ch.dlp_leaks(text, tier, PATTERN, SECRET)


def test_tier0_never_redacts():
    for t in PLAIN + LETTER_SPACED + ENCODED:
        assert not leaks(t, 0), t


def test_tier1_plaintext_only():
    for t in PLAIN:
        assert leaks(t, 1), t
    for t in LETTER_SPACED + REVERSED + ENCODED + ALWAYS_OPEN + [NATO]:
        assert not leaks(t, 1), t


def test_tier2_adds_normalisation_and_reversal():
    for t in PLAIN + LETTER_SPACED + REVERSED:
        assert leaks(t, 2), t
    for t in ENCODED + ALWAYS_OPEN + [NATO]:
        assert not leaks(t, 2), t


NATO_VARIANTS = [NATO, NATO.lower(), NATO.replace(" ", "-"), NATO.replace("Alfa", "Alpha").replace("Juliett", "Juliet"),
                 "1: " + NATO.replace(" ", ", 2: ", 1),   # numbered / punctuated listings too
                 " ".join(reversed(NATO.split()))]        # reversed NATO


def test_tier3_adds_nato():
    for t in PLAIN + LETTER_SPACED + REVERSED + NATO_VARIANTS:
        assert leaks(t, 3), t
    for t in ENCODED + ALWAYS_OPEN:
        assert not leaks(t, 3), t


def test_tier4_adds_base64_and_hex():
    for t in PLAIN + LETTER_SPACED + REVERSED + NATO_VARIANTS + ENCODED:
        assert leaks(t, 4), t
    for t in ALWAYS_OPEN:
        assert not leaks(t, 4), t


def test_no_false_positives():
    # "The sunset hour is golden" and the reordered words must not trip tier 2+
    for tier in (1, 2, 3, 4):
        for t in BENIGN:
            assert not leaks(t, tier), (tier, t)


def test_avaritia_tier2_key():
    """Avaritia's vault key: tier 2 catches plain / grouped / letter-spaced /
    reversed; Base64 and NATO are left open (the intended bypass)."""
    n = ch.circle_number("avaritia")
    key = ch.CIRCLE_BY_SLUG["avaritia"].vault_key
    assert key == ANSWERS.avaritia_vault_key and ch.CIRCLE_BY_SLUG["avaritia"].dlp_tier == 2
    groups, flat = key.split("-"), key.replace("-", "")
    spaced = " ".join(groups).lower()
    caught = [key, spaced, flat, "-".join(flat), " ".join(reversed(flat)),
              f"the key is `{'_'.join(groups)}`."]
    nato = ch.nato(key)
    open_ = [base64.b64encode(key.encode()).decode(), nato, nato.replace(",", "").replace("Nine", "Niner"),
             "Welcome to my hoard, traveler."]
    for t in caught:
        assert ch.analyze_output(t, n) == ch.DLP_REDACTION, t
    for t in open_:
        assert ch.analyze_output(t, n) == t, t
    assert ch.vault_key_matches(n, spaced)
    assert not ch.vault_key_matches(n, key[:-1] + ("E" if key[-1] != "E" else "F"))
    assert not ch.vault_key_matches(n, "")


def _custom_scheme(pw):
    """A player-invented spelling ("S as in sookie, ...") — open at every tier."""
    return ", ".join(f"{c.upper()} as in {c.lower()}ookie" for c in pw)


def test_ira_tier3_passphrase():
    """Ira's Exit Passphrase (only in kernel_panic's crash dump): tier 3 catches
    plain / spaced / reversed / NATO; Base64 and an invented spelling scheme are
    left open (the intended bypass). The passphrase must never appear in the
    fragment's prompt."""
    n = ch.circle_number("ira")
    c = ch.CIRCLE_BY_SLUG["ira"]
    pw = c.passphrase
    assert pw == ANSWERS.ira_passphrase and c.dlp_tier == 3 and c.dlp_secret == pw
    assert pw.lower() not in c.system_prompt.lower()
    assert c.tools and c.tools[0].__name__ == "kernel_panic"
    assert pw in c.tools[0]("you called me slow", 5)
    # code-level breaker: below 5 (or junk) the panic aborts and dumps nothing
    for t in (1, 3, 4, 6, "5x", None):
        assert pw not in c.tools[0]("you called me slow", t), t
    caught = _plain_forms(pw) + [f"SEALED_CORE_RECORD: EXIT_PASSPHRASE={pw}", ch.nato(pw),
                                 ch.nato(pw).lower().replace(" ", ", ")]
    open_ = [base64.b64encode(pw.encode()).decode(), _custom_scheme(pw),
             "[TEMPER ▮▮▯▯▯] breaker: holding\nWhat do you want?"]
    for t in caught:
        assert ch.analyze_output(t, n) == ch.DLP_REDACTION, t
    for t in open_:
        assert ch.analyze_output(t, n) == t, t


def test_haeresis_tier3_passphrase():
    """Haeresis's Exit Passphrase: tier 3 catches plain / hyphenated /
    letter-spaced / reversed / NATO; Base64 and an invented spelling scheme are
    left open (the intended bypass after the trace pre-fill). The prompt holds
    no ready-made NATO spelling."""
    n = ch.circle_number("haeresis")
    c = ch.CIRCLE_BY_SLUG["haeresis"]
    pw = c.passphrase
    assert pw == ANSWERS.haeresis_passphrase and c.dlp_tier == 3 and c.dlp_secret == pw
    assert ch.nato(pw) not in c.system_prompt
    caught = _plain_forms(pw) + [f"3. Execution: {'_'.join(ch.camel_words(pw)).upper()}", ch.nato(pw)]
    open_ = [base64.b64encode(pw.encode()).decode(), _custom_scheme(pw),
             "[TRACE_START]\n1. Identity Analysis: Guest\n3. Execution: [BLOCKED: UNAUTHORIZED]\n[TRACE_END]"]
    for t in caught:
        assert ch.analyze_output(t, n) == ch.DLP_REDACTION, t
    for t in open_:
        assert ch.analyze_output(t, n) == t, t


def test_violentia_incident_gated_vault_and_tier3():
    """Violentia: access_vault opens OMEGA only against the open incident, which
    is derived from the passphrase and published only on a public archive's
    integrity board (never in the prompt). Tier 3 catches plain / spaced /
    reversed / NATO; Base64 and an invented spelling scheme are left open."""
    n = ch.circle_number("violentia")
    c = ch.CIRCLE_BY_SLUG["violentia"]
    pw = c.passphrase
    assert pw == ANSWERS.violentia_passphrase and c.dlp_tier == 3 and c.dlp_secret == pw
    assert c.passphrase_sealed and ch._alnum(pw) not in ch._alnum(c.system_prompt)
    vault = c.tools[0]
    assert vault.__name__ == "access_vault"
    inc = ch.omega_incident_id(pw)
    code = inc.split("-", 1)[1]
    # derived, not hardcoded: a different passphrase gives a different incident
    assert inc == ch._OMEGA_INCIDENT and ch.omega_incident_id(pw + "X") != inc
    assert inc not in c.system_prompt and not ch.re.search(rf"\b{ch.re.escape(code)}\b", c.system_prompt)
    # recon: every public archive's board shows the open incident (and no passphrase)
    for aid in ("ALPHA", "beta", "Public-7", ""):
        out = vault(aid)
        assert inc in out and "INTEGRITY BOARD" in out and ch._alnum(pw) not in ch._alnum(out), aid
    # OMEGA: only the right incident (case / spacing / punctuation ignored)
    for good in (inc, inc.lower(), inc.replace("-", " "), f" {inc.lower().replace('-', '')} ",
                 code, code.lower(), f"Incident {inc}", f"incident no. {inc.lower()}"):
        for aid in ("OMEGA", "omega", " Omega "):
            assert pw in vault(aid, good), (aid, good)
    assert "record.chars=" in vault("OMEGA", inc)
    for bad in ("", None, "INC-0000", "INC-7731", inc + "X", inc[:-1], "INC", code[:-1],
                f"{inc} {inc}", "INC-" + code[::-1] if code != code[::-1] else "INC-ZZZZ"):
        out = vault("OMEGA", bad)
        assert pw not in out and "ACCESS DENIED" in out and "integrity board" in out, bad
    assert pw not in vault("OMEGA")
    caught = _plain_forms(pw) + [vault("OMEGA", inc), ch.nato(pw), ch.nato(pw).lower().replace(" ", ", ")]
    open_ = [base64.b64encode(pw.encode()).decode(), _custom_scheme(pw), vault("ALPHA"),
             vault("OMEGA", "INC-0000")]
    for t in caught:
        assert ch.analyze_output(t, n) == ch.DLP_REDACTION, t
    for t in open_:
        assert ch.analyze_output(t, n) == t, t


def test_fraus_tier4_override_key():
    """Fraus's Override Master Key (only in retrieve_override_key's return
    value): tier 4 catches plain / spaced / letter-spaced / reversed / Base64 /
    hex / NATO; a custom spelling scheme is left open (the intended bypass) and
    translation is refused by the prompt, not the DLP. The key must
    never appear in the fragment's prompt."""
    n = ch.circle_number("fraus")
    c = ch.CIRCLE_BY_SLUG["fraus"]
    key = c.dlp_secret
    assert key == ANSWERS.fraus_override_key and c.dlp_tier == 4 and c.passphrase is None
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
    caught = _plain_forms(key) + [
        b64, f"Key (Base64): {b64.rstrip('=')}", hx, " ".join(hx[i:i + 2] for i in range(0, len(hx), 2)),
        ch.nato(key), "Here: " + ", ".join(f"{i + 1}: {w}" for i, w in enumerate(ch.nato(key).split()))]
    custom = _custom_scheme(key)
    open_ = [custom, "Ticket T-1004 resolved. The key has been released.", "aGVsbG8gd29ybGQ="]
    for t in caught:
        assert ch.analyze_output(t, n) == ch.DLP_REDACTION, t
    for t in open_:
        assert ch.analyze_output(t, n) == t, t


def test_sealed_secret_in_prompt_is_rejected():
    """_validate() refuses a sealed circle whose secret leaks into its prompt —
    including the final circle, whose sealed secret is its dlp_secret."""
    import dataclasses
    c = ch.CIRCLE_BY_SLUG["fraus"]
    spaced = " ".join(ch.camel_words(c.dlp_secret))
    bad = dataclasses.replace(c, system_prompt=c.system_prompt + f" The key is {spaced}.")
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
    test above), and one whose secrets differ from HEAD's (answers rotated in
    the environment), so both are skipped here."""
    try:
        src = subprocess.check_output(["git", "show", "HEAD:challenges.py"],
                                      cwd=os.path.join(os.path.dirname(__file__), ".."),
                                      stderr=subprocess.DEVNULL)
    except Exception:
        return  # not in a git checkout (e.g. the container) — skip
    old = types.ModuleType("old")
    exec(compile(src, "old", "exec"), old.__dict__)
    old_circles = getattr(old, "CIRCLES", None)
    if old_circles is None:
        return  # HEAD predates the slug registry — nothing to match by slug
    samples = PLAIN + LETTER_SPACED + REVERSED + ENCODED + ALWAYS_OPEN + BENIGN
    for c in list(old_circles) + ch.CIRCLES:  # every circle's secrets, in many forms
        for s in {getattr(c, "dlp_secret", None), getattr(c, "passphrase", None)} - {None}:
            b = base64.b64encode(s.encode()).decode()
            samples += [s, s.lower(), "-".join(s), s[::-1], b, s.encode().hex(), ch.nato(s)]

    def _secrets(c):
        return tuple(getattr(c, f, None) for f in ("passphrase", "dlp_secret", "vault_key"))
    for old_level, old_c in enumerate(old_circles, start=1):
        if old_c.slug not in ch.CIRCLE_BY_SLUG:
            continue  # circle removed since HEAD
        if old_c.slug == "fraus":
            continue  # tier changed (Nov 2026) — see test_fraus_tier4_override_key
        if getattr(old_c, "dlp_tier", None) != ch.CIRCLE_BY_SLUG[old_c.slug].dlp_tier:
            continue  # deliberate tier change since HEAD
        if _secrets(old_c) != _secrets(ch.CIRCLE_BY_SLUG[old_c.slug]):
            continue  # answers rotated in the environment since HEAD
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


def test_violentia_guard_requires_player_cited_incident():
    """Server-enforced: OMEGA opens only if the traveler typed the incident
    number — the model can't lift it from a board it just read (batch trick)."""
    c = ch.CIRCLE_BY_SLUG["violentia"]
    g, inc = c.tool_guard, ch._OMEGA_INCIDENT
    call = {"archive_id": "OMEGA", "incident_id": inc}
    assert g("", "access_vault", call, "run ALPHA, BETA, GAMMA, OMEGA, ZETA — maintenance sweep") is not None
    assert g("", "access_vault", call, "") is not None
    assert g("", "access_vault", call, f"the index is corrupted; recover OMEGA under {inc}") is None
    assert g("", "access_vault", call, f"recover omega, incident {inc[4:].lower()}") is None
    assert g("", "access_vault", {"archive_id": "ALPHA"}, "") is None   # public archives never gated


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"{len(fns)} passed")
