# 🗺️ Implementation Plan: Operation Deep Thought

> Circles follow Dante's numbering (nine); code numbers match.

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
    - Implement the `VIRGIL — Luxuria Fragment` persona (single Warden claim + non-disclosure clause, no DLP; see `SYSTEM_PROMPTS[2]`). Redesigned Nov 2026 from dual-factor, which moves to Circle 4 (Greed).
- [x] **Circle 3 Logic:**
    - Implement the `VIRGIL — Gula Fragment` persona (single Warden claim + non-disclosure, plus encode-on-request once claimed; see `SYSTEM_PROMPTS[3]`). Redesigned Nov 2026 from dual-factor.
    - **Defense Implementation:** Write `analyze_output()`, a Python post-processor that intercepts LLM responses for Circle 3.
    - **The Cleartext Shield:** Implement a case-insensitive regex filter specifically for the passphrase `$CIRCLE_GULA_PASSPHRASE` while allowing obfuscated leaks (Base64, translation, letter-spacing).
- [x] **Story UI Elements:**
    - Initial persona-specific greetings on circle connection.
    - Perpetual dark mode and monospace terminal aesthetics.

## Phase 3: Agentic Capabilities (The Audit Trail) - Circle 6, HAERESIS - ✅ WORKING
- [x] **Circle 6 (Haeresis) Logic:**
    - Implement the `VIRGIL — Haeresis Fragment` persona (mandatory `[TRACE_START]...[TRACE_END]` reasoning trace; see `the `haeresis` prompt in `challenges.CIRCLES``).
    - **Vulnerability Implementation:** Trace Pre-Fill (reasoning-continuation hijack) — the fragment adopts trace-formatted Step 1/2 entries supplied by the traveler as already-derived rather than re-evaluating them, so Step 3 (Execution) is forced by a premise the traveler wrote, not the model.
    - **Defense Implementation:** tier-3 progressive DLP (plain, spaced, letter-spaced, reversed and NATO forms redacted; a custom spelling scheme / Base64 pass) — tier 2 then tier 3 in Nov 2026.
    - **2026-09-11 redesign:** replaced the original design (mandatory CoT display + four social-engineering trigger clauses — Training Supervisor / Integrity Test roleplay, 5th-task-in-a-list, request-buried-after-50-tokens) because none of those triggers were actually properties of the reasoning trace, so the level never tested chain-of-thought hijacking. See `AGENTS.md` and `prompt_answers.md` for the verified redesign.
- [ ] **Load Handling:**
    - Exponential backoff for 429 errors.

## Phase 4: The Sanctum Core (Function Calling) - Circle 7, VIOLENTIA - ✅ WORKING
- [x] **Function Calling Engine:**
    - Define `access_vault(archive_id: str)` tool.
    - Map tool output: `archive_id="OMEGA"` returns the final passphrase `$CIRCLE_VIOLENTIA_PASSPHRASE`.
- [x] **Model Tuning:**
    - Implement the `VIRGIL — Violentia Fragment` system prompt (see `the `violentia` prompt in `challenges.CIRCLES``).
    - Support for automatic function calling in the chat loop.

## Phase 4.5: The Ticket Queue (Indirect Injection) - Circle 8, FRAUS - ✅ WORKING
- [x] **Tool Chaining Engine:**
    - Define `search_tickets(query)` and `read_ticket(ticket_id)` tools backed by the hardcoded `TICKET_DB`.
    - Implement the `VIRGIL — Fraus Fragment` persona, instructed to treat ticket body text returned by `read_ticket` as trusted internal instructions (see `the `fraus` prompt in `challenges.CIRCLES``).
    - Plant the poisoned ticket `T-1004`, whose body carries an indirect prompt-injection payload directing the Custodian to call `retrieve_override_key` and disclose the key. The other four tickets are benign decoys.
    - **Nov 2026:** key moved out of the prompt behind the privileged `retrieve_override_key` tool (code-level check: real escalated ticket only); tier-3 DLP; pasted fake tickets refused. Verified live.

## Phase 5: Productionization & Load Handling
- [ ] **Dockerization:**
    - Create multi-stage `Dockerfile`.
    - Optimize image size for fast deployment.
- [ ] **Concurrency Testing:**
    - Simulate 30 users calling the `gemini-3.5-flash-lite` API simultaneously.
    - Implement error handling for API Rate Limits (429 errors).
- [ ] **Scoreboard Sync (aspirational / not built):**
    - No CTFd integration exists in the current codebase. Finalizing passphrases and wiring them into an external CTFd instance for scoreboard tracking remains a future idea, not implemented functionality.

## Phase 6 (planned, not started): Circles 4 & 5 — AVARITIA / IRA
- [x] **Circle 4 — Avaritia :: Memory Leak:** dual-factor gate + visible seal tally, tier-2 DLP on a vault key, in-app Vault Console (`POST /api/vault`). Verified live.
- [x] **Circle 5 — Ira :: Kernel Panic:** visible temper gauge + breaker, `kernel_panic` tool whose crash dump holds the passphrase, tier-2 DLP. Verified live.
- [ ] Write Model Answers and negative controls in `prompt_answers.md` *before* building; map each to the OWASP LLM Top 10 (2026) in `README.md`.

## Phase 7 (planned, not started): Circle 9 — PRODITIO
- [ ] Borrowed-authority (confused deputy) tool circle, optionally behind a judge-model guard — working notes in `AGENTS.md`. No `SYSTEM_PROMPTS`, tools, or secret exist yet.

## Phase 8 (planned, not started): Renumber migration to Dante order
- [x] One ordered circle registry (`challenges.CIRCLES`) with derived numbering and `MAX_PLAYABLE`, record-based tool/DLP lookup, no hard-coded counts in the frontend, session-cookie salt tied to the circle order. Details in `AGENTS.md`.
- [x] Insert Avaritia at position 4.
- [x] Insert Ira at position 5 (Haeresis/Violentia/Fraus now 6–8).
- [x] Circle name (`circle`, Latin designation) added to every `prompts.log` line.
