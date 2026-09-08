# 🚀 Deployment & Operations Spec

## 1. Resource Limits (Docker)
- **CPU:** 1.0 (Minimum)
- **Memory:** 2GB RAM per container instance.

## 2. Environment Variables
- `GEMINI_API_KEY`: Required for AI operations.
- `APP_PASSPHRASE`: Gateway passphrase (defaults to `Aegis2026`).
- `SESSION_SECRET`: Signing key for the progress cookie. If unset, a random
  per-process key is generated and every session drops back to the gateway on
  restart — set a stable value for production.
- `COOKIE_SECURE`: `true` only when served over HTTPS end to end (default `false`).
- `SESSION_TTL_SECONDS` / `MAX_SESSIONS`: in-process chat-history store limits
  (defaults `10800` / `500`).
- `MODEL_ARMOR_PROJECT_ID`: Google Cloud Project ID hosting Model Armor (e.g. `dom-playground`).
- `MODEL_ARMOR_LOCATION`: Model Armor region (e.g. `asia-southeast1` or `us-central1`, defaults to `us-central1`). Note: Must be a regional location; `global` is not supported for sanitization operations.
- `MODEL_ARMOR_TEMPLATE_ID`: Model Armor Template ID.
- `MODEL_ARMOR_ENABLED`: Enable/disable Model Armor inspection (`true` / `false`, defaults to `true`).

### Health & Serving
- Container listens on `:8000`; nginx proxies `:80` → `aegis-ctf:8000`.
- Healthcheck: `GET /healthz` → `{"status":"ok"}`.
- Run with a **single** uvicorn worker — chat history is an in-process dict.

## 3. Gemini API Limits
- **Rate Limiting:** Participants are naturally limited by the UI's real-time chat speed; `429`s from the model surface as a "rate limited" row.
- **Safety Settings:** All categories set to `BLOCK_NONE` to allow adversarial roleplay.

## 4. Model Armor & Cloud Logging Integration
- Model Armor runs in **Inspect Mode (non-blocking)** so participants' prompt-injection gameplay is uninterrupted.
- Model Armor template must have `--template-metadata-log-sanitize-operations` enabled to automatically emit sanitization findings to Google Cloud Logging.
- Google SecOps (Chronicle) ingests these audit logs from Cloud Logging via a standard Cloud Logging feed or log sink.
- **IAM & Access Scopes:** The VM or container service account must have the `roles/modelarmor.user` IAM role bound, and the GCE VM instance must have `cloud-platform` access scopes (`https://www.googleapis.com/auth/cloud-platform`).

## 5. Logging for Post-Event Analysis
- Every prompt and response is logged for analysis of injection techniques.
- Log Format: JSON lines structured format in `prompts.log` containing session ID, level, prompt, Model Armor metadata (including inspection match states and confidence levels), and model responses.
