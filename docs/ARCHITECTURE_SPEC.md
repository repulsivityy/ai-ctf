# 🏗️ Technical Architecture Specification

## 1. State Management
- **Circle registry:** `challenges.CIRCLES` is the single ordered source of truth for every circle; numbers derive from list position and the cookie salt embeds the order, so reordering resets sessions once.
- **User Session:** a signed cookie tracks progress; `server.py` holds chat history in-process. Tracked:
    - `authenticated`: Boolean for global gateway access.
    - `current_level`: code levels 1–6 today. The target is nine circles in Dante's order (Avaritia 4, Ira 5 and Proditio 9 are planned; Haeresis, Violentia and Fraus will become 6, 7 and 8) — see `AGENTS.md`.
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
    5. Enables `access_vault` tool (Violentia, code level 5 only) or `search_tickets` / `read_ticket` tools (Fraus, code level 6 only) — see `TICKET_DB` in `challenges.py` for the backing ticket-queue data used by Fraus's (code level 6) indirect prompt-injection scenario.
    6. Applies `analyze_output()` DLP filter (Gula, code level 3, and Haeresis, code level 4).
    7. Appends response to session state and renders to UI.

## 3. Concurrency
- Progress lives in a signed session cookie; the only server-side state is per-session Gemini chat history (in-process dict, single worker).
