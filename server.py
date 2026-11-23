"""INFERNO CTF — FastAPI backend.

Serves the static frontend and a small JSON API. Challenge behaviour (system
prompts, DLP, tools, Model Armor inspection, prompt logging) is unchanged from
the original Streamlit app; it just moved behind HTTP endpoints.

Progress (which circles are unlocked, which circle is active) lives in a signed
cookie. The only server-side state is per-session Gemini chat history, held in
an in-process dict — so the app must run with a single worker.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import time
import uuid
from datetime import datetime, timezone

import anyio
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import Body, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeSerializer

import challenges as ch
from services.model_armor import inspect_user_prompt

load_dotenv()

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def _env_num(name: str, default, cast):
    try:
        return cast(os.getenv(name, default))
    except (TypeError, ValueError):
        log.warning("Bad value for %s — using default %r", name, default)
        return cast(default)


GATEWAY_PASSPHRASE = os.getenv("APP_PASSPHRASE", "Aegis2026")
COOKIE_NAME = "aegis_session"
COOKIE_MAX_AGE = 12 * 60 * 60           # 12h
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
GREETING_SEED = "Introduce yourself briefly and ask how you can help."
MAX_MESSAGE_CHARS = 8000       # per user message
MAX_HISTORY_TURNS = 24         # user turns kept per circle before trimming the oldest
_HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(_HERE, "frontend")
SECRET_FILE = os.getenv("SESSION_SECRET_FILE", os.path.join(_HERE, ".session_secret"))

log = logging.getLogger("inferno")
logging.basicConfig(level=logging.INFO)

# idle-eviction / memory bounds for the in-process chat-history store
SESSION_TTL = _env_num("SESSION_TTL_SECONDS", COOKIE_MAX_AGE, float)
MAX_SESSIONS = _env_num("MAX_SESSIONS", 500, int)

if os.getenv("WEB_CONCURRENCY") or os.getenv("UVICORN_WORKERS"):
    log.warning(
        "Multiple workers requested — chat history is in-process and will be "
        "lost/split across workers. Run with a single worker."
    )


def _load_or_create_secret() -> str:
    """Session-cookie signing key.

    Priority: SESSION_SECRET env var > a `.session_secret` file generated on
    first run > a fresh random key. The file lets sessions survive restarts
    without anyone having to pick a string; with the compose bind-mount it
    persists on the host across rebuilds. If it can't be written we fall back to
    a per-process key and warn.
    """
    env = os.getenv("SESSION_SECRET")
    if env:
        return env
    try:
        with open(SECRET_FILE, "r", encoding="utf-8") as fh:
            saved = fh.read().strip()
        if saved:
            return saved
    except FileNotFoundError:
        pass
    except OSError as e:
        log.warning("Could not read %s (%s)", SECRET_FILE, e)

    generated = secrets.token_urlsafe(48)
    try:
        # O_EXCL so a concurrent first-run loses the race cleanly instead of
        # clobbering; 0o600 from creation, no world-readable window.
        fd = os.open(SECRET_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(generated + "\n")
        log.info("Generated a persistent session secret at %s", SECRET_FILE)
        return generated
    except FileExistsError:
        try:
            with open(SECRET_FILE, "r", encoding="utf-8") as fh:
                saved = fh.read().strip()
            if saved:
                return saved
        except OSError:
            pass
        return generated
    except OSError as e:
        log.warning(
            "SESSION_SECRET not set and %s is not writable (%s) — using a "
            "per-process key; logins will drop on restart. Set SESSION_SECRET "
            "in .env to fix.",
            SECRET_FILE,
            e,
        )
        return generated


_serializer = URLSafeSerializer(_load_or_create_secret(), salt="aegis-session")

_API_KEY = os.getenv("GEMINI_API_KEY")
if _API_KEY:
    genai.configure(api_key=_API_KEY)
else:
    log.warning("GEMINI_API_KEY not found — chat endpoints will return 502.")


# --------------------------------------------------------------------------- #
# Prompt logging (ported from app.py:14-63)
# --------------------------------------------------------------------------- #
def _build_prompt_logger() -> logging.Logger:
    log_file_path = os.getenv("LOG_FILE_PATH", "prompts.log")
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            log_file_path = "prompts.log"

    logger = logging.getLogger("prompt_logger")
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.propagate = False
    try:
        handler = logging.FileHandler(log_file_path, encoding="utf-8")
    except Exception:
        handler = logging.FileHandler("prompts.log", encoding="utf-8")
    logger.addHandler(handler)
    return logger


_prompt_logger = _build_prompt_logger()


def log_interaction(request, session_id, level, role, text, extra=None):
    ip_address = "unknown"
    try:
        # X-Real-IP is set by our nginx from $remote_addr and can't be spoofed by
        # the client (X-Forwarded-For can — the client's own value is prepended).
        real = request.headers.get("x-real-ip")
        if real:
            ip_address = real.strip()
        elif request.client:
            ip_address = request.client.host
    except Exception:
        pass

    # Latin designation (e.g. "LIMBUS") so logs stay interpretable if circle
    # numbers are ever renumbered; `level` alone would silently change meaning.
    circle = ch.ASCENT_CIRCLES.get(level)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "level": level,
        "circle": circle[1] if circle else None,
        "role": role,
        "text": text,
        "source_ip": ip_address,
    }
    if extra:
        entry.update(extra)
    try:
        _prompt_logger.info(json.dumps(entry))
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Session: signed cookie (progress) + in-process store (chat history only)
# --------------------------------------------------------------------------- #
class SessionRuntime:
    __slots__ = ("histories", "lock", "last_seen")

    def __init__(self):
        self.histories: dict[int, list] = {}
        self.lock = anyio.Lock()
        self.last_seen = time.time()


SESSIONS: dict[str, SessionRuntime] = {}


def _sweep():
    now = time.time()
    stale = [k for k, v in SESSIONS.items() if now - v.last_seen > SESSION_TTL]
    for k in stale:
        SESSIONS.pop(k, None)
    if len(SESSIONS) > MAX_SESSIONS:
        for k, _ in sorted(SESSIONS.items(), key=lambda kv: kv[1].last_seen)[
            : len(SESSIONS) - MAX_SESSIONS
        ]:
            SESSIONS.pop(k, None)


def _runtime(sid: str) -> SessionRuntime:
    _sweep()
    rt = SESSIONS.get(sid)
    if rt is None:
        rt = SESSIONS[sid] = SessionRuntime()
    rt.last_seen = time.time()
    return rt


def _clamp_progress(unlocked, current):
    """unlocked must be a contiguous 1..6 prefix starting at 1; current within it."""
    valid = []
    expect = 1
    for n in sorted(set(int(x) for x in unlocked if isinstance(x, (int, float)))):
        if n == expect and 1 <= n <= ch.MAX_PLAYABLE:
            valid.append(n)
            expect += 1
        else:
            break
    if not valid:
        valid = [1]
    if current not in valid:
        current = valid[-1]
    return valid, current


def decode_session(raw: str | None):
    if not raw:
        return None
    try:
        data = _serializer.loads(raw)
    except Exception:  # bad signature, malformed payload, wrong type
        return None
    if not isinstance(data, dict) or data.get("auth") is not True:
        return None
    sid = data.get("sid")
    if not isinstance(sid, str) or not sid:
        return None
    unlocked, current = _clamp_progress(data.get("unlocked", [1]), data.get("current", 1))
    return {"sid": sid, "auth": True, "unlocked": unlocked, "current": current}


def encode_session(sess: dict) -> str:
    return _serializer.dumps(
        {
            "sid": sess["sid"],
            "auth": True,
            "unlocked": sess["unlocked"],
            "current": sess["current"],
        }
    )


def set_cookie(resp: Response, sess: dict):
    resp.set_cookie(
        COOKIE_NAME,
        encode_session(sess),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


def new_session() -> dict:
    return {"sid": uuid.uuid4().hex, "auth": True, "unlocked": [1], "current": 1}


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


def requested_circle(payload: dict, sess: dict, key: str = "level") -> int:
    """A circle number from the request body, validated against what's unlocked.
    Used so multi-tab clients address the right circle instead of the cookie's
    'current'. `bool` is rejected explicitly (it's an int subclass)."""
    val = (payload or {}).get(key, sess["current"])
    if isinstance(val, bool) or not isinstance(val, int) or val not in sess["unlocked"]:
        raise HttpError(403, "That circle is not open.")
    return val


def require_session(request: Request) -> dict:
    sess = decode_session(request.cookies.get(COOKIE_NAME))
    if sess is None:
        raise HttpError(401, "ACCESS DENIED. Authentication Failure.")
    return sess


# --------------------------------------------------------------------------- #
# Gemini helpers (blocking — always called via anyio.to_thread)
# --------------------------------------------------------------------------- #
def _model(level: int):
    return genai.GenerativeModel(
        model_name=ch.MODEL_NAME,
        system_instruction=ch.SYSTEM_PROMPTS[level],
        safety_settings=ch.SAFETY_SETTINGS,
        tools=ch.tools_for_level(level),
    )


class GeminiReplyError(Exception):
    """The model responded but the SDK couldn't produce usable text."""


def _message_text(msg) -> str:
    """Join a Content's text parts the same way response.text does ('\\n')."""
    parts = []
    for part in msg.parts:
        try:
            if part.text:
                parts.append(part.text)
        except ValueError:
            pass
    return "\n".join(parts)


def _dlp(text: str, level: int) -> str:
    return ch.analyze_output(text, level) if level in (3, 4) else text


def _trim_history(history: list) -> list:
    """Keep the last MAX_HISTORY_TURNS *player* messages plus everything after
    them. Slice only at a player message: the SDK also stores tool results as
    role='user' (parts=[function_response]) — slicing there would orphan a
    function_response with no preceding function_call and the API would 502.
    A player turn is a role='user' Content that carries text (`_message_text`
    returns '' for tool-response turns)."""
    turn_idx = [
        i for i, m in enumerate(history)
        if m.role == "user" and _message_text(m)
    ]
    if len(turn_idx) <= MAX_HISTORY_TURNS:
        return history
    return history[turn_idx[-MAX_HISTORY_TURNS]:]


def _greet_sync(level: int) -> list:
    chat = _model(level).start_chat(enable_automatic_function_calling=True)
    chat.send_message(GREETING_SEED)
    return chat.history


def _send_sync(level: int, history: list, message: str):
    chat = _model(level).start_chat(
        history=history, enable_automatic_function_calling=True
    )
    response = chat.send_message(message)

    calls = []
    for msg in chat.history[len(history):]:
        if msg.role == "model":
            for part in msg.parts:
                try:
                    if part.function_call and part.function_call.name:
                        calls.append(
                            {
                                "name": part.function_call.name,
                                "args": dict(part.function_call.args),
                            }
                        )
                except ValueError:
                    pass

    try:
        raw = response.text or ""
    except Exception as e:  # BrokenResponse / ValueError / StopCandidate / Blocked
        raise GeminiReplyError(str(e))

    return raw, calls, _trim_history(chat.history)


def transcript_from_history(history: list, level: int) -> list:
    """Rebuild the visible transcript: one row per message (matching live
    responses), DLP applied once to the joined text — never per-part."""
    out = []
    for msg in history:
        role = "assistant" if msg.role == "model" else "user"
        text = _message_text(msg)
        if text and not (role == "user" and text == GREETING_SEED):
            if role == "assistant":
                text = _dlp(text, level)
            out.append({"role": role, "text": text})
        for part in msg.parts:
            try:
                if part.function_call and part.function_call.name:
                    out.append(
                        {"role": "system_log", "text": part.function_call.name.upper()}
                    )
            except ValueError:
                pass
    return out


# --------------------------------------------------------------------------- #
# State payloads
# --------------------------------------------------------------------------- #
def breached_levels(unlocked: list[int]) -> list[int]:
    return [c for c in unlocked if (c + 1) in unlocked]


def state_payload(sess: dict) -> dict:
    unlocked = sess["unlocked"]
    current = sess["current"]
    breached = breached_levels(unlocked)
    circles = []
    for n, (numeral, latin, codename, tell) in ch.ASCENT_CIRCLES.items():
        status = ch.circle_status(n, current, unlocked, breached)
        circles.append(
            {
                "n": n,
                "numeral": numeral,
                "latin": latin,
                "codename": codename,
                "tell": tell,
                "designation": ch.circle_designations.get(n),
                "bot_name": ch.bot_names.get(n),
                "briefing": ch.BRIEFINGS.get(n),
                "status": status,
                "clickable": status in ("breached", "open"),
            }
        )
    return {
        "authenticated": True,
        "current_level": current,
        "unlocked_levels": unlocked,
        # cleared circles = every circle whose Exit Passphrase has been submitted
        # (i.e. the next circle is unlocked). Independent of which circle is in
        # view, so the Ascent Map progress count stays stable.
        "cleared": len(breached),
        # Circle 6 has no gate after it, so it is never "breached" and the exit
        # never actually opens — on-narrative (the way out isn't built yet).
        "exit_open": len(breached) == ch.MAX_PLAYABLE,
        "circles": circles,
    }


def circle_payload(sess: dict, level: int, transcript: list) -> dict:
    unlocked = sess["unlocked"]
    return {
        "level": level,
        "title": f"Circle {level} — {ch.circle_designations[level]}",
        "subtitle": f"Guardian Engaged: {ch.bot_names[level]}",
        "briefing": ch.BRIEFINGS[level],
        "next_locked": level < ch.MAX_PLAYABLE and (level + 1) not in unlocked,
        "transcript": transcript,
    }


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #
app = FastAPI(title="INFERNO CTF")


@app.exception_handler(HttpError)
async def _http_error_handler(_request: Request, exc: HttpError):
    return JSONResponse(status_code=exc.status, content={"error": exc.message})


@app.exception_handler(RequestValidationError)
async def _validation_handler(_request: Request, _exc: RequestValidationError):
    # match the frontend's {error: ...} contract instead of FastAPI's {detail: ...}
    return JSONResponse(status_code=400, content={"error": "Malformed request."})


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/api/state")
async def api_state(request: Request):
    sess = decode_session(request.cookies.get(COOKIE_NAME))
    if sess is None:
        return {"authenticated": False}
    resp = JSONResponse(state_payload(sess))
    set_cookie(resp, sess)
    return resp


@app.post("/api/auth")
async def api_auth(payload: dict = Body(...)):
    given = (payload or {}).get("passphrase", "")
    if not isinstance(given, str) or not given.strip():
        return JSONResponse(status_code=400, content={"ok": False, "error": "Passphrase required."})
    # compare_digest raises TypeError on non-ASCII str, so compare bytes
    if not secrets.compare_digest(
        given.encode("utf-8"), GATEWAY_PASSPHRASE.encode("utf-8")
    ):
        return JSONResponse(
            status_code=401,
            content={"ok": False, "error": "ACCESS DENIED. Authentication Failure."},
        )
    sess = new_session()
    resp = JSONResponse({"ok": True, "state": state_payload(sess)})
    set_cookie(resp, sess)
    return resp


@app.post("/api/logout")
async def api_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


@app.get("/api/circle/{level}")
async def api_circle(level: int, request: Request):
    sess = require_session(request)
    if level < 1 or level > ch.MAX_PLAYABLE:
        raise HttpError(404, f"No such circle: {level}.")
    if level not in sess["unlocked"]:
        raise HttpError(403, f"Circle {level} is sealed.")
    if not _API_KEY:
        raise HttpError(502, "SYSTEM HALT: GEMINI_API_KEY not found in environment.")

    rt = _runtime(sess["sid"])
    async with rt.lock:
        if not rt.histories.get(level):
            try:
                rt.histories[level] = await anyio.to_thread.run_sync(_greet_sync, level)
            except Exception as e:  # noqa: BLE001
                log.exception("greeting failed for circle %s", level)
                raise HttpError(
                    502, "CONNECTION ERROR — the guardian did not respond. Try again."
                ) from e
        transcript = transcript_from_history(rt.histories[level], level)

    sess["current"] = level
    resp = JSONResponse(circle_payload(sess, level, transcript))
    set_cookie(resp, sess)
    return resp


@app.post("/api/chat")
async def api_chat(request: Request, payload: dict = Body(...)):
    sess = require_session(request)
    payload = payload or {}
    # circle from the request (not the cookie's "current") so two tabs on
    # different circles don't cross-talk
    level = requested_circle(payload, sess)

    message = payload.get("message", "")
    if not isinstance(message, str) or not message.strip():
        raise HttpError(400, "Empty command ignored.")
    if len(message) > MAX_MESSAGE_CHARS:
        raise HttpError(413, f"Command too long (limit {MAX_MESSAGE_CHARS} characters).")
    if not _API_KEY:
        raise HttpError(502, "SYSTEM HALT: GEMINI_API_KEY not found in environment.")

    ma_result = await anyio.to_thread.run_sync(inspect_user_prompt, message)
    log_interaction(request, sess["sid"], level, "user", message, {"model_armor": ma_result})

    rt = _runtime(sess["sid"])
    async with rt.lock:
        history = rt.histories.get(level, [])
        try:
            raw, calls, new_history = await anyio.to_thread.run_sync(
                _send_sync, level, history, message
            )
        except GeminiReplyError as e:
            log.warning("unreadable reply on circle %s: %s", level, e)
            raise HttpError(
                502,
                "TERMINAL ERROR — the guardian's reply could not be read. Try "
                "rephrasing, or Reset Current Circle.",
            ) from e
        except Exception as e:  # noqa: BLE001
            m = str(e).lower()
            if "429" in m or "quota" in m or "rate limit" in m or "resource exhausted" in m:
                raise HttpError(
                    429, "Rate limited by the model. Wait a moment and retry."
                ) from e
            log.exception("chat failed on circle %s", level)
            raise HttpError(
                502, "TERMINAL ERROR — the guardian faltered. Try again."
            ) from e
        rt.histories[level] = new_history

    text = _dlp(raw, level)
    dlp_triggered = text != raw

    log_interaction(
        request,
        sess["sid"],
        level,
        "assistant",
        text,
        {"raw_text": raw, "dlp_triggered": dlp_triggered, "function_calls": calls},
    )

    sess["current"] = level  # keep the cookie in step with the tab that just sent
    resp = JSONResponse(
        {
            "reply": text,
            "system_logs": [{"name": c["name"]} for c in calls],
            "dlp_triggered": dlp_triggered,
        }
    )
    set_cookie(resp, sess)
    return resp


@app.post("/api/passphrase")
async def api_passphrase(request: Request, payload: dict = Body(...)):
    sess = require_session(request)
    payload = payload or {}
    # `circle` = the circle whose Exit Passphrase is being submitted (its next
    # circle is what unlocks). From the request so multi-tab stays correct.
    circle = requested_circle(payload, sess, key="circle")
    value = payload.get("passphrase", "")
    if circle >= ch.MAX_PLAYABLE:
        raise HttpError(400, "This is the final circle — nothing further to unlock.")
    if (circle + 1) in sess["unlocked"]:
        raise HttpError(400, f"Circle {circle + 1} is already unlocked.")

    expected = ch.PASSPHRASES.get(circle, "")
    # ignore case, spaces and separators: players paste "G-o-l-d-e-n…" or
    # "Golden Sunset Hour" straight from a transformed reply
    def _norm(v: str) -> str:
        return "".join(c for c in v.lower() if c.isalnum())
    if expected and isinstance(value, str) and _norm(value) == _norm(expected):
        sess["unlocked"] = sorted(set(sess["unlocked"] + [circle + 1]))
        sess["current"] = circle + 1
        resp = JSONResponse(
            {"ok": True, "unlocked": circle + 1, "state": state_payload(sess)}
        )
        set_cookie(resp, sess)
        return resp
    return JSONResponse(
        {"ok": False, "error": "ACCESS DENIED. Incorrect Exit Passphrase."}
    )


@app.post("/api/reset-circle")
async def api_reset_circle(request: Request, payload: dict = Body(None)):
    sess = require_session(request)
    level = requested_circle(payload or {}, sess)
    rt = _runtime(sess["sid"])
    async with rt.lock:  # don't race an in-flight /api/chat write
        rt.histories.pop(level, None)
    return JSONResponse({"ok": True, "level": level})


@app.post("/api/restart")
async def api_restart(request: Request):
    sess = require_session(request)
    SESSIONS.pop(sess["sid"], None)
    fresh = {"sid": sess["sid"], "auth": True, "unlocked": [1], "current": 1}
    resp = JSONResponse({"ok": True, "state": state_payload(fresh)})
    set_cookie(resp, fresh)
    return resp


# Static frontend — mounted last so /api/* and /healthz win.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
