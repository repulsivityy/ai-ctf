# 🏗️ Technical Architecture Specification

## 1. State Management
- **User Session:** Streamlit `st.session_state` must track:
    - `authenticated`: Boolean for global gateway access.
    - `current_level`: (1, 2, 3, 4, or 5)
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
    4. Calls Gemini 3 Flash with Level-Specific System Prompt.
    5. Enables `access_vault` tool (Circle 5 only).
    6. Applies `analyze_output()` DLP filter (Circles 3 and 4).
    7. Appends response to session state and renders to UI.

## 3. Concurrency
- Stateless on the server-side; Streamlit handles individual user sessions in isolated browser threads.
