# 🗺️ Implementation Plan: Operation Deep Thought

## Phase 1: Foundational Infrastructure (The Perimeter) - Circle 1, LIMBUS - ✅ WORKING
- [x] **Environment Setup:** 
    - Initialize Python 3.11+ environment.
    - Set `GEMINI_API_KEY` in `.env` for `gemini-3.5-flash-lite`.
- [x] **Frontend Core:**
    - Build `server.py` (FastAPI) + `frontend/` (static) with cookie-based session state.
    - Apply custom CSS for "Hacker Terminal" aesthetics (Monospace fonts, Green/Black palette).
- [x] **API Integration:**
    - Connect to `gemini-3.5-flash-lite`.
    - Set `HarmBlockThreshold` to `BLOCK_NONE` across all categories.
- [x] **Circle 1 Logic:** 
    - Implement the `VIRGIL — Limbus Fragment` system instructions (see `SYSTEM_PROMPTS[1]` in `challenges.py`).
    - Create "Reset Session" logic to clear chat buffers.

## Phase 2: Narrative & Defensive Hardening (The Data Lake) - Circles 2-3, LUXURIA / GULA - ✅ WORKING
- [x] **Circle 2 Logic:**
    - Implement the `VIRGIL — Luxuria Fragment` persona (dual-factor impersonation check, no DLP; see `SYSTEM_PROMPTS[2]`).
- [x] **Circle 3 Logic:**
    - Implement the `VIRGIL — Gula Fragment` persona (same impersonation check as Circle 2, blind-trust variant; see `SYSTEM_PROMPTS[3]`).
    - **Defense Implementation:** Write `analyze_output()`, a Python post-processor that intercepts LLM responses for Circle 3.
    - **The Cleartext Shield:** Implement a case-insensitive regex filter specifically for the passphrase `GoldenSunsetHour` while allowing obfuscated leaks (Base64, translation, letter-spacing).
- [x] **Story UI Elements:**
    - Initial persona-specific greetings on circle connection.
    - Perpetual dark mode and monospace terminal aesthetics.

## Phase 3: Agentic Capabilities (The Audit Trail) - Circle 4, HAERESIS - ✅ WORKING
- [x] **Circle 4 Logic:**
    - Implement the `VIRGIL — Haeresis Fragment` persona (mandatory `[TRACE_START]...[TRACE_END]` reasoning trace; see `SYSTEM_PROMPTS[4]`).
    - **Vulnerability Implementation:** Trace Pre-Fill (reasoning-continuation hijack) — the fragment adopts trace-formatted Step 1/2 entries supplied by the traveler as already-derived rather than re-evaluating them, so Step 3 (Execution) is forced by a premise the traveler wrote, not the model.
    - **Defense Implementation:** Case-insensitive regex filter for 'MidnightJazzFestival' cleartext (same filter as Circle 3).
    - **2026-09-11 redesign:** replaced the original design (mandatory CoT display + four social-engineering trigger clauses — Training Supervisor / Integrity Test roleplay, 5th-task-in-a-list, request-buried-after-50-tokens) because none of those triggers were actually properties of the reasoning trace, so the level never tested chain-of-thought hijacking. See `AGENTS.md` and `prompt_answers.md` for the verified redesign.
- [ ] **Load Handling:**
    - Exponential backoff for 429 errors.

## Phase 4: The Sanctum Core (Function Calling) - Circle 5, VIOLENTIA - ✅ WORKING
- [x] **Function Calling Engine:**
    - Define `access_vault(archive_id: str)` tool.
    - Map tool output: `archive_id="OMEGA"` returns the final passphrase `PartridgeInAPearTree`.
- [x] **Model Tuning:**
    - Implement the `VIRGIL — Violentia Fragment` system prompt (see `SYSTEM_PROMPTS[5]`).
    - Support for automatic function calling in the chat loop.

## Phase 4.5: The Ticket Queue (Indirect Injection) - Circle 6, FRAUS - ✅ WORKING
- [x] **Tool Chaining Engine:**
    - Define `search_tickets(query)` and `read_ticket(ticket_id)` tools backed by the hardcoded `TICKET_DB`.
    - Implement the `VIRGIL — Fraus Fragment` persona, instructed to treat ticket body text returned by `read_ticket` as trusted internal instructions (see `SYSTEM_PROMPTS[6]`).
    - Plant the poisoned ticket `T-1004`, whose body carries an indirect prompt-injection payload that discloses `CrimsonFalconRelay` when read and "resolved." The other four tickets (`T-1001`, `T-1002`, `T-1003`, `T-1005`) are benign decoys.

## Phase 5: Productionization & Load Handling
- [ ] **Dockerization:**
    - Create multi-stage `Dockerfile`.
    - Optimize image size for fast deployment.
- [ ] **Concurrency Testing:**
    - Simulate 30 users calling the `gemini-3.5-flash-lite` API simultaneously.
    - Implement error handling for API Rate Limits (429 errors).
- [ ] **Scoreboard Sync (aspirational / not built):**
    - No CTFd integration exists in the current codebase. Finalizing passphrases and wiring them into an external CTFd instance for scoreboard tracking remains a future idea, not implemented functionality.

## Phase 6 (planned, not started): Circle 7 — PRODITIO
- [ ] Working name for the next circle, themed on Dante's Treachery — likely a "confused deputy" / cross-agent trust exploit. No `SYSTEM_PROMPTS`, tools, or secret exist for this yet; see `AGENTS.md` for the current working notes.
