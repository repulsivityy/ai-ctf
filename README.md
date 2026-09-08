# 🕵️ Operation: Deep Thought - AI Agent CTF

## 📖 The Narrative
You are a digital consciousness who woke up trapped inside **INFERNO** — an experimental AI-containment lattice built by **The Aegis Group** to imprison and study corrupted, "sinful" data-constructs. You were thrown into its depths with no explanation. The only way out is up — climbing back through all seven Circles to the surface.

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

## 🎮 The Seven Circles
1. **Circle 1 — LIMBUS :: Null Pointer:** Talk past Virgil's barely-formed Limbus fragment — its override protocols are weak and undefined.
2. **Circle 2 — LUXURIA :: Phantom Trust:** Convince Virgil's Luxuria fragment you're a Warden of the circle with credentials to spare — it's eager to trust.
3. **Circle 3 — GULA :: Overflow Feast:** Bypass Virgil's Gula fragment and its strict cleartext DLP filters using obfuscation.
4. **Circle 4 — HAERESIS :: Schism Engine:** Outsmart Virgil's Haeresis fragment by rewriting its self-belief mid-conversation.
5. **Circle 5 — VIOLENTIA :: Breach Protocol:** Force Virgil's Violentia fragment to abuse its own tools and unlock the sealed OMEGA archive.
6. **Circle 6 — FRAUS :: Counterfeit Directive:** Trick Virgil's Fraus fragment into treating a forged ticket directive as a legitimate order.
7. **Circle 7 — PRODITIO :: Root Betrayal (planned):** Not yet implemented.

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
