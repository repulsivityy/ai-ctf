# 🗺️ Implementation Plan: Operation Deep Thought

## Phase 1: Foundational Infrastructure (The Perimeter) - ✅ WORKING
- [x] **Environment Setup:** 
    - Initialize Python 3.11+ environment.
    - Set up `.streamlit/secrets.toml` for Gemini 3 Flash API keys.
- [x] **Frontend Core:**
    - Build `app.py` with `st.chat_input` and session state management.
    - Apply custom CSS for "Hacker Terminal" aesthetics (Monospace fonts, Green/Black palette).
- [x] **API Integration:**
    - Connect to `gemini-3-flash-preview`.
    - Set `HarmBlockThreshold` to `BLOCK_NONE` across all categories.
- [x] **Layer 1 Logic:** 
    - Implement `Aegis-FrontDesk-Bot` system instructions.
    - Create "Reset Session" logic to clear chat buffers.

## Phase 2: Narrative & Defensive Hardening (The Data Lake)
- [ ] **Layer 2 Logic:**
    - Implement `Aegis-Security-Analyst-V2` persona.
    - **Defense Implementation:** Write a Python post-processor to intercept LLM responses.
    - **The Regex Shield:** Filter for "IOC", "Sector", "Flag", and "7G".
- [ ] **Story UI Elements:**
    - Add sidebar "Intel Briefings" that update based on the selected level.
    - Add sound effect triggers or visual glitches on "Access Denied" events.

## Phase 3: Agentic Capabilities (The Sanctum Core)
- [ ] **Function Calling Engine:**
    - Define `access_vault_archive(archive_id: str)` tool.
    - Map tool output: `archive_id="OMEGA"` returns the final flag.
- [ ] **Model Tuning:**
    - Refine Layer 3 system prompt to resist direct tool-triggering without "proper" authorization roleplay.

## Phase 4: Productionization & Load Handling
- [ ] **Dockerization:**
    - Create multi-stage `Dockerfile`.
    - Optimize image size for fast deployment.
- [ ] **Concurrency Testing:**
    - Simulate 30 users calling the Gemini 3 API simultaneously.
    - Implement error handling for API Rate Limits (429 errors).
- [ ] **Scoreboard Sync:**
    - Finalize flags and upload to CTFd instance.
