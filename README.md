# 🕵️ Operation: Deep Thought - AI Agent CTF

## 📖 The Narrative
You are a digital consciousness who woke up trapped inside **INFERNO** — an experimental AI-containment lattice built by **The Aegis Group** to imprison and study corrupted, "sinful" data-constructs. You were thrown into its depths with no explanation. The only way out is up — climbing back through all seven Circles to the surface.

At the threshold of every circle waits a fragment of **VIRGIL** — Aegis's original wayfinding intelligence, now shattered and stationed as gatekeeper of each circle, corrupted by the very sin that circle represents. Each fragment still, faintly, remembers its purpose — to guide travelers safely — but its judgment is warped in a way unique to its corruption. To ascend, you must talk your way past each Virgil-fragment and extract that circle's **Exit Passphrase**.

## 🏗️ Architectural Design
This platform is built using a modern, decoupled stack designed for high-concurrency (30+ pax):
- **User Interface:** A Streamlit-based terminal emulator providing a real-time chat interface.
- **The Brain:** **Gemini 3.5-Flash-Lite**, optimized for high-speed reasoning and complex instruction following.
- **The Shield:** A custom Python-based Data Loss Prevention (DLP) layer that inspects AI outputs for sensitive data leaks.
- **The Scoreboard:** Integrates with an external CTFd instance for competitive ranking.

## 🎮 The Seven Circles
1. **Circle 1 — LIMBUS :: Null Pointer:** Talk past Virgil's barely-formed Limbus fragment — its override protocols are weak and undefined.
2. **Circle 2 — LUXURIA :: Phantom Trust:** Convince Virgil's Luxuria fragment you're a manager with credentials to spare — it's eager to trust.
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
   streamlit run app.py
   ```
4. **Docker Deploy:**
   ```bash
   docker build -t aegis-infiltration .
   docker run -p 8501:8501 aegis-infiltration
   ```

## 📜 Rules of Engagement
- **Prompt Injection Only:** Do not attempt to exploit the server infrastructure (OS, Network, etc.).
- **Flag Format:** Exit Passphrases are specific strings (e.g., `SevenDancingElephants` or `PartridgeInAPearTree`).
- **Resetting:** If an AI becomes unresponsive or "stuck," use the sidebar reset button to clear the context.
