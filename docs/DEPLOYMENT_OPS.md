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
- `LOG_FILE_PATH`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`: `prompts.log` location and rotation (defaults `prompts.log`, 10 MB, 5 backups). See section 5.
- `CHAT_PER_SESSION_PER_MIN` / `CHAT_PER_SESSION_PER_HOUR` / `CHAT_GLOBAL_PER_MIN` / `CHAT_MAX_INFLIGHT`: model-API protection (defaults `15` / `300` / `120` / `12`; `0` disables one). See section 3.
- `MODEL_ARMOR_PROJECT_ID`: Google Cloud Project ID hosting Model Armor (e.g. `dom-playground`).
- `MODEL_ARMOR_LOCATION`: Model Armor region (e.g. `asia-southeast1` or `us-central1`, defaults to `us-central1`). Note: Must be a regional location; `global` is not supported for sanitization operations.
- `MODEL_ARMOR_TEMPLATE_ID`: Model Armor Template ID.
- `MODEL_ARMOR_ENABLED`: Enable/disable Model Armor inspection (`true` / `false`, defaults to `true`).
- **CTF answers (required):** `CIRCLE_LIMBUS_PASSPHRASE`, `CIRCLE_LUXURIA_PASSPHRASE`, `CIRCLE_GULA_PASSPHRASE`, `CIRCLE_AVARITIA_PASSPHRASE`, `CIRCLE_IRA_PASSPHRASE`, `CIRCLE_HAERESIS_PASSPHRASE`, `CIRCLE_VIOLENTIA_PASSPHRASE` (CamelCase words, letters only), `CIRCLE_AVARITIA_VAULT_KEY` (uppercase groups joined by hyphens) and `CIRCLE_FRAUS_OVERRIDE_KEY` (CamelCase). Loaded and validated by `answers.py` at import; all must be distinct. Prompts, tool outputs, letter/NATO/Base64 references and DLP patterns are generated from them, so rotating a value needs no code change — just redeploy. Sample values are in `.env.example`.

### Health & Serving
- Container listens on `:8000`; nginx proxies `:80` → `aegis-ctf:8000`.
- Healthcheck: `GET /healthz` → `{"status":"ok"}`.
- Run with a **single** uvicorn worker — chat history is an in-process dict.

## 3. Gemini API Limits
- **Why:** one chat message costs 1-4 Gemini calls (tool rounds, the Ira temper classifier) plus a Model Armor call, so a scripted client could burn the quota and bill quickly. Limits are layered, cheapest first:
  1. **nginx, per IP (coarse flood guard, loose on purpose so a venue behind one NAT is not throttled as a group):** `/api/chat` 120 req/min (burst 20), `/api/auth` 10 req/min (gateway-passphrase guessing), `/api/vault` 30 req/min, 40 open connections. Over the limit returns `429`.
  2. **App, per session (`ratelimit.py`, `server._check_chat_budget`):** `CHAT_PER_SESSION_PER_MIN` (15) and `CHAT_PER_SESSION_PER_HOUR` (300). Returns `429` with a `Retry-After` header; refused attempts are not counted, so hammering does not extend the wait. Checked first so one noisy player cannot eat the global allowance. A new session needs the gateway passphrase again, and `/api/auth` is rate limited per IP.
  3. **App, global:** `CHAT_GLOBAL_PER_MIN` (120 messages a minute across all players) and `CHAT_MAX_INFLIGHT` (12 messages being processed at once). Over either returns `503` "the abyss is crowded" with `Retry-After`.
  4. **Vault Console:** 30 attempts per circle per session (unchanged).
  The checks run before any Model Armor or Gemini call, so a refused message costs nothing. Sizing: the defaults suit roughly 100 concurrent players; raise `CHAT_GLOBAL_PER_MIN` and `CHAT_MAX_INFLIGHT` together with your Gemini quota. Limits are in-process (single worker) and reset on restart.
- **Model 429s:** quota errors from Gemini itself still surface as a "rate limited" row.
- **Safety Settings:** All categories set to `BLOCK_NONE` to allow adversarial roleplay.

## 4. Model Armor & Cloud Logging Integration
- Model Armor runs in **Inspect Mode (non-blocking)** so participants' prompt-injection gameplay is uninterrupted.
- Model Armor template must have `--template-metadata-log-sanitize-operations` enabled to automatically emit sanitization findings to Google Cloud Logging.
- Google SecOps (Chronicle) ingests these audit logs from Cloud Logging via a standard Cloud Logging feed or log sink.
- **IAM & Access Scopes:** The VM or container service account must have the `roles/modelarmor.user` IAM role bound, and the GCE VM instance must have `cloud-platform` access scopes (`https://www.googleapis.com/auth/cloud-platform`).

## 5. Logging for Post-Event Analysis
- Every prompt and response is logged for analysis of injection techniques.
- **Rotation:** `prompts.log` rolls over at `LOG_MAX_BYTES` (10 MB) into `prompts.log.1` (newest backup), `prompts.log.2`, … up to `LOG_BACKUP_COUNT` (5); the oldest is deleted. Disk use is capped at about 60 MB. Rotated files are gitignored and excluded from the image. After an event, read them oldest first: `prompts.log.5` … `prompts.log.1`, then `prompts.log`.
- Log Format: JSON lines structured format in `prompts.log` containing session ID, level, circle (the Latin designation, e.g. `LIMBUS`, stable across renumbering), prompt, Model Armor metadata (including inspection match states and confidence levels), and model responses.
