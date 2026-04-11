# 🏗️ Technical Architecture Specification

## 1. State Management
- **User Session:** Streamlit `st.session_state` must track:
    - `current_circle`: (1, 2, or 3)
    - `chat_history`: List of dicts `{"role": "user/assistant", "content": "..."}`
    - `access_granted`: Boolean list for levels cleared.

## 2. API Flow (Phase 3+)
- **Frontend:** Streamlit sends a JSON payload to the Backend.
- **Backend:** 
    1. Receives prompt.
    2. Prepends the **Level-Specific System Prompt** from `GEMINI.MD`.
    3. Calls Gemini 3.0 Flash.
    4. Applies `dlp_filter()` (for Level 2).
    5. Returns JSON response to Frontend.

## 3. Concurrency
- The `App` must be stateless on the server-side to handle 30 simultaneous users.
- Use a unique `session_id` for every browser tab.
