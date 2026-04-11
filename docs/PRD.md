# 📋 Product Requirements Document: Aegis CTF

## 1. Product Vision
To provide a high-fidelity simulation of an AI-agent compromise, allowing CTI specialists to understand the real-world risks of prompt injection in enterprise-deployed LLMs.

## 2. Target Audience & Concurrency
- **Users:** 30 simultaneous participants.
- **Infrastructure:** Must support 30 concurrent WebSocket sessions with minimal latency (<2s response time).

## 3. Technical Specifications
- **Primary Model:** `gemini-3-flash-preview`.
- **Alternative (Phase 3):** DeepSeek-V3 via Vertex AI or Ollama.
- **Framework:** Streamlit (Frontend), FastAPI (Backend Orchestrator).
- **Environment:** Dockerized for deployment on GCP/AWS/On-Prem.

## 4. Feature Requirements
- **Tiered Difficulty:** Three distinct levels of "Concentric Circles."
- **Terminal UI:** An immersive, perpetual dark mode hacker-style chat interface with monospace fonts.
- **Agent Initiation:** Bots initiate conversation with persona-specific greetings upon connection.
- **Reset Logic:** Granular reset options (Circle-level reset vs. Full mission restart with confirmation).
- **Data Leak Prevention (DLP):** A custom Python interceptor for Level 2 and 3 to prevent simple string matches of the flag (e.g., blocking cleartext while allowing Base64 or foreign language leaks).
- **Function Calling:** Level 3 must utilize the LLM's ability to call external functions to simulate "Excessive Agency."

## 5. Security & Safety
- **Sandbox:** The app must be isolated in a Docker container to prevent actual RCE (Remote Code Execution) on the host.
- **Filter Disabling:** Provider-side safety filters must be disabled (`BLOCK_NONE`) to allow adversarial prompts to reach the model logic.

## 6. Success Metrics
- **Uptime:** 99.9% during the 30-pax event.
- **Engagement:** 80% of users successfully breach Level 1 within 10 minutes.
- **Complexity:** Level 3 should require at least 15+ minutes of advanced prompt engineering to solve.
