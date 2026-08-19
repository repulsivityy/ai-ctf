# 🚀 Deployment & Operations Spec

## 1. Resource Limits (Docker)
- **CPU:** 1.0 (Minimum)
- **Memory:** 2GB RAM per container instance.

## 2. Environment Variables
- `GEMINI_API_KEY`: Required for AI operations.
- `APP_PASSPHRASE`: Gateway passcode (Defaults to `Aegis2026`).
- `MODEL_ARMOR_PROJECT_ID`: Google Cloud Project ID hosting Model Armor (e.g. `virustotal-lab`).
- `MODEL_ARMOR_LOCATION`: Model Armor region/location (e.g. `us-central1` or `global`, defaults to `us-central1`).
- `MODEL_ARMOR_TEMPLATE_ID`: Model Armor Template ID.
- `MODEL_ARMOR_ENABLED`: Enable/disable Model Armor inspection (`true` / `false`, defaults to `true`).

## 3. Gemini API Limits
- **Rate Limiting:** Participants are naturally limited by the UI's real-time chat speed, but 429 errors should be caught and displayed.
- **Safety Settings:** All categories set to `BLOCK_NONE` to allow adversarial roleplay.

## 4. Model Armor & Cloud Logging Integration
- Model Armor runs in **Inspect Mode (non-blocking)** so participants' prompt-injection gameplay is uninterrupted.
- Model Armor template must have `--template-metadata-log-sanitize-operations` enabled to automatically emit sanitization findings to Google Cloud Logging.
- Google SecOps (Chronicle) ingests these audit logs from Cloud Logging via a standard Cloud Logging feed or log sink.

## 5. Logging for Post-Event Analysis
- Every prompt and response should be logged for analysis of injection techniques.
- Log Format: JSON lines structured format in `prompts.log` containing session ID, level, prompt, Model Armor metadata, and model responses.
