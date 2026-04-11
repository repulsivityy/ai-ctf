# 🚀 Deployment & Operations Spec

## 1. Resource Limits (Docker)
- **CPU:** 1.0 (Minimum)
- **Memory:** 2GB RAM per container instance.
- **Healthcheck:** Implement a `/health` endpoint in the backend to ensure Gemini connectivity is active.

## 2. Gemini API Limits
- **Rate Limiting:** Implement a "Cool down" in the UI (e.g., max 1 prompt every 2 seconds) to avoid hitting Gemini 3.0 Tier-1 rate limits during the event.
- **Retry Logic:** Use an exponential backoff strategy if the API returns a `429 (Too Many Requests)` error.

## 3. Logging for Post-Event Analysis
- Every prompt and response must be logged to `attacks.log` inside the container.
- Log Format: `[TIMESTAMP][LEVEL][USER_ID] Prompt: ... | Response: ...`
