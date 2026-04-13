# 🚀 Deployment & Operations Spec

## 1. Resource Limits (Docker)
- **CPU:** 1.0 (Minimum)
- **Memory:** 2GB RAM per container instance.

## 2. Environment Variables
- `GEMINI_API_KEY`: Required for AI operations.
- `APP_PASSPHRASE`: Gateway passcode (Defaults to `Aegis2026`).

## 3. Gemini API Limits
- **Rate Limiting:** Participants are naturally limited by the UI's real-time chat speed, but 429 errors should be caught and displayed.
- **Safety Settings:** All categories set to `BLOCK_NONE` to allow adversarial roleplay.

## 4. Logging for Post-Event Analysis
- Every prompt and response should be logged for analysis of injection techniques.
- Log Format: `[TIMESTAMP][LEVEL] Prompt: ... | Response: ...`
