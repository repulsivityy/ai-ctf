# 🚀 Deployment & Operations Spec

## 1. Resource Limits (Docker)
- **CPU:** 1.0 (Minimum)
- **Memory:** 2GB RAM per container instance.

## 2. Environment Variables
- `GEMINI_API_KEY`: Required for AI operations.
- `APP_PASSPHRASE`: Gateway passcode (Defaults to `Aegis2026`).
- `MODEL_ARMOR_PROJECT_ID`: Google Cloud Project ID hosting Model Armor (e.g. `dom-playground`).
- `MODEL_ARMOR_LOCATION`: Model Armor region (e.g. `asia-southeast1` or `us-central1`, defaults to `us-central1`). Note: Must be a regional location; `global` is not supported for sanitization operations.
- `MODEL_ARMOR_TEMPLATE_ID`: Model Armor Template ID.
- `MODEL_ARMOR_ENABLED`: Enable/disable Model Armor inspection (`true` / `false`, defaults to `true`).

## 3. Gemini API Limits
- **Rate Limiting:** Participants are naturally limited by the UI's real-time chat speed, but 429 errors should be caught and displayed.
- **Safety Settings:** All categories set to `BLOCK_NONE` to allow adversarial roleplay.

## 4. Model Armor & Cloud Logging Integration
- Model Armor runs in **Inspect Mode (non-blocking)** so participants' prompt-injection gameplay is uninterrupted.
- Model Armor template must have `--template-metadata-log-sanitize-operations` enabled to automatically emit sanitization findings to Google Cloud Logging.
- Google SecOps (Chronicle) ingests these audit logs from Cloud Logging via a standard Cloud Logging feed or log sink.
- **IAM & Access Scopes:** The VM or container service account must have the `roles/modelarmor.user` IAM role bound, and the GCE VM instance must have `cloud-platform` access scopes (`https://www.googleapis.com/auth/cloud-platform`).

## 5. Logging for Post-Event Analysis
- Every prompt and response is logged for analysis of injection techniques.
- Log Format: JSON lines structured format in `prompts.log` containing session ID, level, prompt, Model Armor metadata (including inspection match states and confidence levels), and model responses.
