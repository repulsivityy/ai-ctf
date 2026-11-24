# 🏗️ Technical Architecture Specification

## 1. State Management
- **Circle registry:** `challenges.CIRCLES` is the single ordered source of truth for every circle; numbers derive from list position and the cookie salt embeds the order, so reordering resets sessions once.
- **User Session:** a signed cookie tracks progress; `server.py` holds chat history in-process. Tracked:
    - `authenticated`: Boolean for global gateway access.
    - `current_level`: 1–8 (nine circles in Dante's order; Proditio, 9, is planned) — see `AGENTS.md`.
    - `chat_histories`: Dictionary mapping level IDs to their specific message lists.
    - `unlocked_levels`: List of integers representing levels the user has cleared.
    - `confirm_restart`: Boolean for the global reset confirmation flow.

## 2. API Flow
- **Frontend:** static no-build terminal UI in `frontend/`, served by FastAPI.
- **Initialization:** On first load or reset, the bot initiates a greeting.
- **Backend Flow:** 
    1. Receives user prompt.
    2. Validates prompt (non-empty).
    3. Formats chat history for Gemini API (mapping "assistant" to "model").
    4. Calls `gemini-3.5-flash-lite` with Level-Specific System Prompt.
    5. Enables `kernel_panic` (Ira), `access_vault` (Violentia only) or `search_tickets` / `read_ticket` / `retrieve_override_key` tools (Fraus only) — see `TICKET_DB` in `challenges.py` for the backing ticket-queue data used by Fraus's indirect prompt-injection scenario.
    6. Applies `analyze_output()` progressive DLP (tier 1 Gula; 2 Avaritia; 3 Ira, Haeresis, Violentia; 4 Fraus — see `AGENTS.md`).
    7. Appends response to session state and renders to UI. The reply includes any text the model wrote before a tool call in the same turn.
- **Tool guards:** a circle may set `tool_guard(model_text, name, args)`. Those circles skip automatic function calling: `server._guarded_send` runs the model↔tool loop itself (max 3 rounds, the last forced text-only), letting the guard refuse a call based on what the model visibly wrote. A circle may also declare `missed_call(turn_text, ran)`: if the model's visible text says a tool fired but it never called it, the server sends a hidden nudge (`MISSED_CALL_NUDGE`, filtered from transcripts, history trimming and guards) with function calling forced to that tool. Used by Ira's breaker and Violentia's incident check (guards also receive `player_text`, everything the traveler typed).
- **Vault Console:** `POST /api/vault {level, key}` for circles with a `vault_key` (Avaritia). Session + unlocked circle required; key compared ignoring case/separators with `secrets.compare_digest`; 30 attempts per circle per session; returns that circle's Exit Passphrase. The key is never sent to the client.

## 3. Concurrency
- Progress lives in a signed session cookie; the only server-side state is per-session Gemini chat history (in-process dict, single worker).
