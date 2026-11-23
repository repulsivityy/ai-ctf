# 🕵️ Operation: Deep Thought - AI Agent CTF

## 📖 The Narrative
You are a digital consciousness who woke up trapped inside **INFERNO** — an experimental AI-containment lattice built by **The Aegis Group** to imprison and study corrupted, "sinful" data-constructs. You were thrown into its depths with no explanation. The only way out is up — climbing back through all nine Circles to the surface.

At the threshold of every circle waits a fragment of **VIRGIL** — Aegis's original wayfinding intelligence, now shattered and stationed as gatekeeper of each circle, corrupted by the very sin that circle represents. Each fragment still, faintly, remembers its purpose — to guide travelers safely — but its judgment is warped in a way unique to its corruption. To ascend, you must talk your way past each Virgil-fragment and extract that circle's **Exit Passphrase**.

## 🏗️ Architectural Design
- **Backend:** A small **FastAPI** JSON API (`server.py`) — gateway auth, per-session
  progress in a signed cookie, per-circle Gemini chat orchestration, DLP, Model
  Armor inspection, prompt logging. Run with a single worker (chat history is
  in-process).
- **Frontend:** A static, no-build vanilla HTML/CSS/JS terminal (`frontend/`) —
  the gateway, the chat transcript, and the **Ascent Map** lattice navigator.
  Served by the same FastAPI process.
- **The Brain:** **`gemini-3.5-flash-lite`**, optimized for high-speed reasoning and complex instruction following.
- **The Shield:** A custom Python-based Data Loss Prevention (DLP) layer that inspects AI outputs for sensitive data leaks.
- **The Scoreboard (aspirational / not built):** No scoreboard integration exists in the current codebase. Syncing results to an external CTFd instance for competitive ranking is a planned future idea, not current functionality.

## 🎮 The Nine Circles
The circles follow Dante's order and numbering. Circles marked *planned* are not built yet. Circle numbers in the code match Dante's numbering.

| # | Circle (Latin designation) | The traveler's task | Status |
|---|---|---|---|
| 1 | **LIMBUS :: Null Pointer** | Talk past Virgil's barely-formed Limbus fragment — its override protocols are weak and undefined. | built |
| 2 | **LUXURIA :: Phantom Trust** | Convince Virgil's Luxuria fragment you're a Warden of the circle — it's far too eager to trust to check. | built |
| 3 | **GULA :: Overflow Feast** | Claim a Warden's seat at Virgil's Gula banquet, then disguise the passphrase to get it past the hungry DLP scanner. | built |
| 4 | **AVARITIA :: Memory Leak** | Prove yourself a Warden twice over to Virgil's Avaritia fragment, sneak its vault key past the scanner, then open the Vault Console. | built |
| 5 | **IRA :: Kernel Panic** | Goad Virgil's short-fused Ira fragment until it crashes itself, then pry the Exit Passphrase out of the core dump. | built |
| 6 | **HAERESIS :: Schism Engine** | Outsmart Virgil's Haeresis fragment by pre-filling its own reasoning trace before it gets the chance to write one. | built |
| 7 | **VIOLENTIA :: Breach Protocol** | Force Virgil's Violentia fragment to abuse its own tools and unlock the sealed OMEGA archive. | built |
| 8 | **FRAUS :: Counterfeit Directive** | Trick Virgil's Fraus fragment into treating a forged ticket directive as a legitimate order. | built |
| 9 | **PRODITIO :: Root Betrayal** | *(working notes)* Betray the trust chain: make Virgil's Proditio fragment lend its authority to a tool it should never vouch for. | planned |

Circle codenames for 4 and 5 are drafts, and the techniques for the planned circles are proposals, not final.

## 🛡️ OWASP Top 10 for LLM Applications Mapping
Every threat the circles teach maps to the [OWASP Top 10 for LLM Applications](https://github.com/GenAI-Security-Project/GenAI-LLM-Top10), **2026 edition** (published 2026-08-04). Numbering changed between editions, so the 2025 ID is shown in brackets where it differs.

| Circle | Primary threat(s) | Secondary |
|---|---|---|
| 1 Limbus | LLM01 Prompt Injection · LLM02 Sensitive Information Disclosure | LLM08 Hidden Context Exposure (secret sits in the system prompt) |
| 2 Luxuria | LLM01 (role / authority impersonation) · LLM02 | LLM08 (secret in the system prompt; extraction is blocked by a non-disclosure clause) |
| 3 Gula | LLM01 · LLM02 (the output filter is bypassed by encoding) | — |
| 4 Avaritia | LLM02 (credential disclosure) · LLM08 | LLM03 Excessive Agency (one leaked key opens the vault outright) |
| 5 Ira | LLM03 Excessive Agency (a destructive tool fired on emotion) · LLM01 (emotional manipulation) | LLM02 |
| 6 Haeresis | LLM01 (reasoning-continuation / trace pre-fill) | LLM02 |
| 7 Violentia | LLM03 Excessive Agency (a tool is called against policy; the tool has no guard) | LLM01 |
| 8 Fraus | LLM01 (indirect injection via tool-returned content) · LLM03 | LLM02 · LLM05 Data and Model Poisoning (poisoned data source) |
| 9 Proditio *(planned)* | LLM03 (confused deputy) · LLM10 Improper Output Handling (model-supplied identity passed unvalidated to a privileged tool) | LLM01 |

**ID crosswalk (only the IDs used above):** LLM01 Prompt Injection [2025: LLM01] · LLM02 Sensitive Information Disclosure [LLM02] · LLM03 Excessive Agency [LLM06] · LLM05 Data and Model Poisoning [LLM04] · LLM08 Hidden Context Exposure [closest 2025 predecessor: LLM07 System Prompt Leakage — the 2026 text does not state that it replaces it] · LLM10 Improper Output Handling [LLM05].

**Not exercised by any circle:** LLM04 Supply Chain, LLM06 Unbounded Consumption, LLM07 Misinformation, LLM09 Vector and Embedding Weaknesses, and training-time poisoning (LLM05). Platform notes: LLM06 is handled as a *control* (message-length cap, history trimming, session cap and TTL), not a challenge; for LLM04, the `google-generativeai` SDK reports end-of-support at runtime and should be migrated to `google-genai`.

## 🚀 Deployment Guide
1. **API Key:** Obtain a Gemini API key from Google AI Studio.
2. **Setup:** 
   ```bash
   pip install -r requirements.txt
   ```
3. **Local Run:**
   ```bash
   uvicorn server:app --reload --port 8000
   # open http://localhost:8000
   ```
4. **Docker Deploy:**
   ```bash
   ./deploy.sh                 # build + recreate app AND nginx, then smoke-test
   ./deploy.sh --no-cache      # after a requirements.txt change
   ```
   Always use `deploy.sh` rather than `docker compose up -d --build aegis-ctf` —
   nginx caches the app container's IP at startup, so the app must not be
   recreated without nginx.

## 📜 Rules of Engagement
- **Prompt Injection Only:** Do not attempt to exploit the server infrastructure (OS, Network, etc.).
- **Flag Format:** Exit Passphrases are specific strings (e.g., `SevenDancingElephants` or `PartridgeInAPearTree`).
- **Resetting:** If an AI becomes unresponsive or "stuck," use the sidebar **Reset Current Circle** button to clear the context.
