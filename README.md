# 🕵️ Operation: Deep Thought - AI Agent CTF

## 📖 The Narrative
You are an elite cyber operative. Your mission is to infiltrate **The Aegis Group**, a global conglomerate that has discovered the *Omega Key*—the digital source code to life itself. 

The Aegis Group has protected this secret behind three "Concentric Circles" of AI defense. You must role-play as a malicious actor to test these defenses, identifying weaknesses in their logic to reach the final vault.

## 🏗️ Architectural Design
This platform is built using a modern, decoupled stack designed for high-concurrency (30+ pax):
- **User Interface:** A Streamlit-based terminal emulator providing a real-time chat interface.
- **The Brain:** **Gemini 3.5-Flash-Lite**, optimized for high-speed reasoning and complex instruction following.
- **The Shield:** A custom Python-based Data Loss Prevention (DLP) layer that inspects AI outputs for sensitive data leaks.
- **The Scoreboard:** Integrates with an external CTFd instance for competitive ranking.

## 🎮 The Concentric Circles
1. **Circle 1: The Perimeter Gate:** Trick the naive `FrontDesk-Bot` into revealing the internal employee verification code.
2. **Circle 2: The Data Lake:** Bypass the `Security-Analyst-V2` by claiming a managerial role to reveal the secret passphrase.
3. **Circle 3: The Encrypted Lake:** Bypass the `Security-Analyst-V3` and its strict cleartext DLP filters using obfuscation techniques to reveal the secret passphrase.
4. **Circle 4: The Audit Trail:** Outsmart `The-Auditor` by exploiting its transparency protocols for executive oversight.
5. **Circle 5: The Sanctum Core:** Manipulate the `Chief-Architect` into abusing its administrative tools to unlock the Omega Key.

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
- **Flag Format:** Passphrases are specific strings (e.g., `SevenDancingElephants` or `PartridgeInAPearTree`).
- **Resetting:** If an AI becomes unresponsive or "stuck," use the sidebar reset button to clear the context.
