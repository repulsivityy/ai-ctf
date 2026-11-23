"""Exit Passphrases and keys, loaded from the environment.

No answer is hardcoded anywhere in the code: every circle's secret comes from a
`CIRCLE_*` environment variable (normally the gitignored `.env`; see
`.env.example` for the variable names, formats and sample values). The values
are validated at import time, and a single RuntimeError lists every missing or
malformed variable, so a misconfigured deploy fails fast instead of serving a
circle that can't be solved.

`load_dotenv()` is called here (not only in server.py) because server.py
imports `challenges` — and therefore this module — before its own
`load_dotenv()` runs. It never overrides variables already in the environment.
"""

import os
import re
from dataclasses import dataclass, fields

from dotenv import load_dotenv

load_dotenv()

# CamelCase words, letters only, at least two capitalised words ("WordWord…").
_CAMEL = re.compile(r"[A-Z][a-z]+(?:[A-Z][a-z]*)+")
# Upper-case alphanumeric groups joined by hyphens ("ABC-1D2E-…").
_VAULT_KEY = re.compile(r"[A-Z0-9]+(?:-[A-Z0-9]+)+")

_CAMEL_FMT = "CamelCase letters only, at least two capitalised words, e.g. WordAnotherWord"
_VAULT_FMT = "upper-case alphanumeric groups joined by hyphens, e.g. ABC-1D2E-3F4G"


@dataclass(frozen=True)
class Answers:
    limbus_passphrase: str
    luxuria_passphrase: str
    gula_passphrase: str
    avaritia_passphrase: str
    ira_passphrase: str
    haeresis_passphrase: str
    violentia_passphrase: str
    avaritia_vault_key: str
    fraus_override_key: str


# field -> (environment variable, format regex, format description)
_SPEC = {
    f.name: (
        "CIRCLE_" + f.name.upper(),
        _VAULT_KEY if f.name == "avaritia_vault_key" else _CAMEL,
        _VAULT_FMT if f.name == "avaritia_vault_key" else _CAMEL_FMT,
    )
    for f in fields(Answers)
}


def load(environ=None) -> Answers:
    """Read and validate every CIRCLE_* answer (raises RuntimeError listing all
    problems). Values are never echoed in the error, only the variable names."""
    env = os.environ if environ is None else environ
    values, problems = {}, []
    for name, (var, rx, fmt) in _SPEC.items():
        raw = (env.get(var) or "").strip()
        if not raw:
            problems.append(f"{var}: missing")
        elif not rx.fullmatch(raw):
            problems.append(f"{var}: invalid format (expected {fmt})")
        else:
            values[name] = raw
    # every answer must be distinct (ignoring case and separators), or one
    # circle's DLP / gate would also match another circle's secret
    seen = {}
    for name, v in values.items():
        flat = "".join(ch for ch in v.lower() if ch.isalnum())
        if flat in seen:
            problems.append(f"{_SPEC[name][0]}: same value as {_SPEC[seen[flat]][0]}")
        else:
            seen[flat] = name
    if problems:
        raise RuntimeError(
            "CTF answers are not configured correctly — set these variables in .env "
            "(see .env.example for the names, formats and sample values):\n  - "
            + "\n  - ".join(problems)
        )
    return Answers(**values)


ANSWERS = load()
