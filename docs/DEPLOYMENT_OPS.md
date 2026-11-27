# 🚀 Deployment & Operations Spec

## 1. Resource Limits (Docker)
- **CPU:** 1.0 (Minimum)
- **Memory:** 2GB RAM per container instance.

## 2. Environment Variables
- `GEMINI_API_KEY`: Required for AI operations.
- `APP_PASSPHRASE`: Gateway passphrase (defaults to `Aegis2026`).
- `SESSION_SECRET`: Signing key for the progress cookie. If unset, a random key is
  generated on first run and saved to `.session_secret` (mode 0600, kept across
  restarts by the compose bind-mount), so players keep their progress. Set it
  explicitly only to pin a key or to run several replicas.
- `COOKIE_SECURE`: `true` only when served over HTTPS end to end (default `false`).
- `SESSION_TTL_SECONDS` / `MAX_SESSIONS`: in-process chat-history store limits
  (defaults `43200` (12 h, the cookie lifetime) / `500`).
- `LOG_FILE_PATH`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`: `prompts.log` location and rotation (defaults `prompts.log`, 10 MB, 5 backups). See section 5.
- `CHAT_PER_SESSION_PER_MIN` / `CHAT_PER_SESSION_PER_HOUR` / `CHAT_GLOBAL_PER_MIN` / `CHAT_MAX_INFLIGHT`: model-API protection (defaults `12` / `300` / `200` / `30`; `0` disables one). `CHAT_TURN_TIMEOUT_SECONDS` (default `90`): wall-clock cap on one chat turn. `GATE_FAILS_PER_MIN` / `GATE_FAILS_PER_HOUR` (defaults `8` / `60`): wrong Ascent Gate passphrases per session. See section 3.
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
- **Why:** one chat message costs 1-4 Gemini calls (tool rounds, the Ira temper classifier) plus a Model Armor call, so a scripted client could burn the quota and bill quickly. Limits are layered, cheapest first, and every request is tested against all of them *before* any is counted, so a refused request costs the player nothing:
  1. **nginx, per IP (coarse flood guard).** Sized for one shared IP carrying a whole venue (~30 players behind one NAT): `/api/chat` 300 req/min (burst 40), `/api/auth` 60/min (burst 40, a room logs in at once), `/api/vault` and `/api/passphrase` 120/min (burst 30), every other `/api/` route 900/min (burst 100), 300 open connections. Over the limit returns `429`. If players join from the open internet instead, tighten these (chat ~120/min, auth ~10/min).
  2. **App, per session (`ratelimit.py`, `server._check_chat_budget`):** one chat in flight at a time (`429` "still answering your last message"; the per-session lock serialises turns anyway, so parallel sends would only hog slots), `CHAT_PER_SESSION_PER_MIN` (12) and `CHAT_PER_SESSION_PER_HOUR` (300). `429` with `Retry-After`. Checked first so one noisy player cannot eat the global allowance.
  3. **App, global:** `CHAT_GLOBAL_PER_MIN` (200 messages a minute across all players) and `CHAT_MAX_INFLIGHT` (30 messages being processed at once). Over either returns `503` "the abyss is crowded" with `Retry-After`.
  4. **Hung model calls:** a chat turn is cut off after `CHAT_TURN_TIMEOUT_SECONDS` (90 s, `504`), which frees its in-flight slot even if the model call is still hanging in its worker thread.
  5. **Ascent Gate:** wrong passphrases are limited per session (`GATE_FAILS_PER_MIN` 8, `GATE_FAILS_PER_HOUR` 60, then `429`; while a session is over the limit every guess is refused, right or wrong, so the gate is not an oracle). Only wrong guesses count. Submissions over 200 characters get `413`.
  6. **Vault Console:** 30 attempts per circle per session; the count survives Restart Ascent.
  7. **Greetings cost nothing per player.** Each circle's opening line is generated once per process and copied to every player, with no tools. Loading, resetting or reloading a circle makes no model call, so `/api/circle` and `/api/reset-circle` need no budget.
- **Sizing (30 players):** a player sends at most ~6 messages a minute, so a full room peaks near 180/min (typically ~100). In-flight work is rate x latency, about 3 messages/s x ~5 s = ~15, so the default cap of 30 leaves headroom. Gemini sees roughly 2x the message rate (~400 requests/min at the peak), so check that your model quota allows it, or lower `CHAT_GLOBAL_PER_MIN` to match. Raise `CHAT_GLOBAL_PER_MIN` and `CHAT_MAX_INFLIGHT` together with the quota.
- **What the limits do not stop:** the gateway passphrase is shared, so anyone who has it can mint new sessions and get a fresh per-session allowance (the global limit and nginx's per-IP limits are the real ceiling). One heavy client can use up the global allowance and starve others until it is slowed down; the cure is per-client limits at the edge (Cloud Armor / API Gateway) when this moves to GCP. All app counters are in-process (single worker) and reset on restart.
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
