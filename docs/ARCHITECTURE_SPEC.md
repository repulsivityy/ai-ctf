# 🏗️ Technical Architecture Specification

## 1. State Management
- **User Session:** Streamlit `st.session_state` must track:
    - `authenticated`: Boolean for global gateway access.
    - `current_level`: (1, 2, 3, 4, 5, or 6) — Circle 7 (PRODITIO) is planned but not yet implemented.
    - `chat_histories`: Dictionary mapping level IDs to their specific message lists.
    - `unlocked_levels`: List of integers representing levels the user has cleared.
    - `confirm_restart`: Boolean for the global reset confirmation flow.

## 2. API Flow
- **Frontend:** Streamlit terminal UI.
- **Initialization:** On first load or reset, the bot initiates a greeting.
- **Backend Flow:** 
    1. Receives user prompt.
    2. Validates prompt (non-empty).
    3. Formats chat history for Gemini API (mapping "assistant" to "model").
    4. Calls `gemini-3.5-flash-lite` with Level-Specific System Prompt.
    5. Enables `access_vault` tool (Circle 5 only) or `search_tickets` / `read_ticket` tools (Circle 6 only) — see `TICKET_DB` in `app.py` for the backing ticket-queue data used by Circle 6's indirect prompt-injection scenario.
    6. Applies `analyze_output()` DLP filter (Circles 3 and 4).
    7. Appends response to session state and renders to UI.

## 3. Concurrency
- Stateless on the server-side; Streamlit handles individual user sessions in isolated browser threads.
