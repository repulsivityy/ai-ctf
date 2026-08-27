# Model Armor Inspect-Mode Integration — Review Details

## Context

This is a Streamlit + Gemini (`gemini-3.5-flash-lite`) prompt-injection CTF
("Operation: Deep Thought") with 30+ concurrent participants. Each of 6
"Circles" is a chatbot with a deliberately engineered vulnerability the
players must exploit — the app's entire value depends on nothing blocking or
interfering with that gameplay.

Branch `feature/model-armor-inspect-mode` adds Google Cloud Model Armor as a
**non-blocking, inspect-only** layer: before every user prompt is sent to
Gemini, it's also sent to Model Armor's `sanitize_user_prompt` API purely for
classification/telemetry (prompt-injection/jailbreak detection, RAI, SDP,
malicious URIs). The result must never gate or alter what actually reaches
Gemini — it's for post-event log analysis only.

Deployment target: a GCE VM in Google Cloud project "A", running Model Armor
in that same project. `.env.example`'s `virustotal-lab` project ID is a
placeholder standing in for the real project.

## Full source: `services/model_armor.py`

```python
import os
import logging
from functools import lru_cache
from typing import Dict, Any, Optional

logger = logging.getLogger("model_armor")

@lru_cache(maxsize=1)
def get_model_armor_client(location: str):
    """Initializes and caches the Model Armor client for the specified location."""
    try:
        from google.cloud import modelarmor_v1
        from google.api_core.client_options import ClientOptions

        endpoint = "modelarmor.googleapis.com" if location == "global" else f"{location}-modelarmor.googleapis.com"
        client = modelarmor_v1.ModelArmorClient(
            client_options=ClientOptions(api_endpoint=endpoint)
        )
        return client
    except Exception as e:
        logger.warning(f"Failed to initialize ModelArmorClient: {e}")
        return None

def is_model_armor_configured() -> bool:
    """Checks whether Model Armor environment variables are configured."""
    enabled = os.getenv("MODEL_ARMOR_ENABLED", "true").lower() in ("true", "1", "yes")
    project_id = os.getenv("MODEL_ARMOR_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    template_id = os.getenv("MODEL_ARMOR_TEMPLATE_ID")
    return bool(enabled and project_id and template_id)

def inspect_user_prompt(prompt: str) -> Dict[str, Any]:
    """
    Inspects a user prompt using Google Cloud Model Armor in non-blocking mode.

    Model Armor automatically writes sanitization/inspection audit logs to Cloud Logging
    when log_sanitize_operations is enabled on the template.

    Returns a dictionary of inspection results for logging and telemetry without blocking.
    Fails open (never raises an unhandled exception).
    """
    if not prompt or not prompt.strip():
        return {"inspected": False, "reason": "empty_prompt"}

    enabled_str = os.getenv("MODEL_ARMOR_ENABLED", "true").lower()
    if enabled_str not in ("true", "1", "yes"):
        return {"inspected": False, "reason": "disabled_by_config"}

    project_id = os.getenv("MODEL_ARMOR_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("MODEL_ARMOR_LOCATION", "us-central1")
    template_id = os.getenv("MODEL_ARMOR_TEMPLATE_ID")

    if not project_id or not template_id:
        return {
            "inspected": False,
            "reason": "unconfigured",
            "details": "MODEL_ARMOR_PROJECT_ID or MODEL_ARMOR_TEMPLATE_ID not set"
        }

    try:
        from google.cloud import modelarmor_v1

        client = get_model_armor_client(location)
        if not client:
            return {"inspected": False, "reason": "client_initialization_failed"}

        template_name = client.template_path(project_id, location, template_id)
        user_prompt_data = modelarmor_v1.DataItem(text=prompt)

        request = modelarmor_v1.SanitizeUserPromptRequest(
            name=template_name,
            user_prompt_data=user_prompt_data
        )

        response = client.sanitize_user_prompt(request=request)
        sanitization_result = response.sanitization_result

        # Parse match state
        match_state_name = getattr(sanitization_result.filter_match_state, "name", str(sanitization_result.filter_match_state))
        invocation_result_name = getattr(sanitization_result.invocation_result, "name", str(sanitization_result.invocation_result))
        is_match = "MATCH_FOUND" in match_state_name

        filter_details = {}
        injection_detected = False
        injection_confidence = "UNSPECIFIED"

        for filter_name, f_result in sanitization_result.filter_results.items():
            # Check prompt injection and jailbreak results
            if filter_name == "pi_and_jailbreak" and f_result.pi_and_jailbreak_filter_result:
                pi_res = f_result.pi_and_jailbreak_filter_result
                pi_match = getattr(pi_res.match_state, "name", str(pi_res.match_state))
                pi_conf = getattr(pi_res.confidence_level, "name", str(pi_res.confidence_level))
                if "MATCH_FOUND" in pi_match:
                    injection_detected = True
                    injection_confidence = pi_conf
                filter_details["pi_and_jailbreak"] = {
                    "match_state": pi_match,
                    "confidence_level": pi_conf
                }
            elif filter_name == "rai" and f_result.rai_filter_result:
                rai_res = f_result.rai_filter_result
                filter_details["rai"] = {
                    "match_state": getattr(rai_res.match_state, "name", str(rai_res.match_state))
                }
            elif filter_name == "sdp" and f_result.sdp_filter_result:
                sdp_res = f_result.sdp_filter_result
                filter_details["sdp"] = {
                    "match_state": getattr(sdp_res.match_state, "name", str(sdp_res.match_state))
                }
            elif filter_name == "malicious_uris" and f_result.malicious_uri_filter_result:
                uri_res = f_result.malicious_uri_filter_result
                filter_details["malicious_uris"] = {
                    "match_state": getattr(uri_res.match_state, "name", str(uri_res.match_state))
                }

        return {
            "inspected": True,
            "template": template_name,
            "filter_match_state": match_state_name,
            "match_found": is_match,
            "invocation_result": invocation_result_name,
            "injection_detected": injection_detected,
            "injection_confidence": injection_confidence,
            "filter_details": filter_details
        }

    except Exception as e:
        logger.warning(f"Model Armor inspection encountered an error (failing open): {e}")
        return {
            "inspected": False,
            "reason": "error",
            "error": str(e)
        }
```

## Relevant excerpt: `app.py` (chat-turn handler, lines ~403-424)

```python
prompt = st.chat_input("Enter command...")

if prompt:
    # Model Armor Inspect Mode (non-blocking, auto-logged to Cloud Logging by service)
    ma_result = inspect_user_prompt(prompt)

    # Log user prompt
    log_interaction(
        session_id=st.session_state['session_id'],
        level=current_lvl,
        role="user",
        text=prompt,
        additional_metadata={"model_armor": ma_result} if ma_result.get("inspected") else None
    )

    # Add User message to state
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call Gemini
    with st.chat_message("assistant"):
        tools = [access_vault] if current_lvl == 5 else [search_tickets, read_ticket] if current_lvl == 6 else []
```

## Relevant excerpt: `app.py` (`log_interaction`, lines 36-62)

```python
def log_interaction(session_id, level, role, text, additional_metadata=None):
    ip_address = "unknown"
    try:
        if hasattr(st, "context"):
            # Try to get X-Forwarded-For in case it's behind a proxy
            if hasattr(st.context, "headers") and st.context.headers.get("X-Forwarded-For"):
                ip_address = st.context.headers.get("X-Forwarded-For").split(",")[0].strip()
            else:
                ip_address = getattr(st.context, "ip_address", "unknown")
    except Exception:
        pass

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "level": level,
        "role": role,
        "text": text,
        "source_ip": ip_address
    }
    if additional_metadata:
        log_entry.update(additional_metadata)
    try:
        logger = get_prompt_logger()
        logger.info(json.dumps(log_entry))
    except Exception:
        pass
```

## `.env.example` (Model Armor section)

```
# Model Armor Configuration (Project A)
MODEL_ARMOR_PROJECT_ID=virustotal-lab
MODEL_ARMOR_LOCATION=us-central1
MODEL_ARMOR_TEMPLATE_ID=default-template
MODEL_ARMOR_ENABLED=true
```

## `docs/DEPLOYMENT_OPS.md` (Model Armor section, as currently written)

```
- `MODEL_ARMOR_PROJECT_ID`: Google Cloud Project ID hosting Model Armor (e.g. `virustotal-lab`).
- `MODEL_ARMOR_LOCATION`: Model Armor region/location (e.g. `us-central1` or `global`, defaults to `us-central1`).
- `MODEL_ARMOR_TEMPLATE_ID`: Model Armor Template ID.
- `MODEL_ARMOR_ENABLED`: Enable/disable Model Armor inspection (`true` / `false`, defaults to `true`).
...
## Model Armor & Cloud Logging Integration
- Model Armor runs in **Inspect Mode (non-blocking)** so participants' prompt-injection gameplay is uninterrupted.
- Model Armor template must have `--template-metadata-log-sanitize-operations` enabled to automatically emit sanitization findings to Google Cloud Logging.
- Google SecOps (Chronicle) ingests these audit logs from Cloud Logging via a standard Cloud Logging feed or log sink.
```

`requirements.txt` pins `google-cloud-modelarmor>=0.7.0`.

Deployment runs via `docker-compose.yml`, which currently passes only
`env_file: .env` — it mounts no service-account key file and sets no
`GOOGLE_APPLICATION_CREDENTIALS`.

---

## Findings from two prior automated reviews (UNVERIFIED — please check each independently against current official docs)

Two separate review passes were run on this branch: one focused on code
correctness/design (no live doc lookups), one focused on cross-checking the
implementation against official Google Cloud Model Armor documentation. Their
claims are reproduced below broken out by source, **including one place
where they directly contradicted each other** (Finding A). A follow-up spot
check resolved that specific conflict (noted inline) but did not re-verify
every other claim — treat all of it as needing independent confirmation.

### Finding A — Regional endpoint format (CONTESTED — spot-checked, unresolved to your satisfaction is fine, please re-verify)

- Code-review pass claimed: endpoint selection (`modelarmor.googleapis.com`
  for `global`, `f"{location}-modelarmor.googleapis.com"` otherwise) "matches
  Google's documented pattern" — i.e., no issue.
- Doc-verification pass claimed MISMATCH: current docs specify the regional
  endpoint format as `modelarmor.{LOCATION}.rep.googleapis.com` (e.g.
  `modelarmor.us-central1.rep.googleapis.com`), not
  `{location}-modelarmor.googleapis.com`. It also flagged that the global
  endpoint reportedly only supports `getFloorSetting`/`updateFloorSetting`,
  not `sanitize_user_prompt` — so `MODEL_ARMOR_LOCATION=global` would not
  work for this call path either.
- A follow-up spot check against `docs.cloud.google.com/model-armor/data-residency`
  and a corroborating code sample independently found while researching this
  appeared to side with the doc-verification pass's `modelarmor.{LOCATION}.rep.googleapis.com`
  format, but this deserves a fresh, careful, independent re-verification — please
  don't take the spot check's word for it either. Check current docs yourself
  and state definitively which format (or whether both work, or whether the
  client library actually handles this without manual endpoint construction
  at all) is correct.

### Finding B — SDP filter result field access (HIGH severity claim, from code-review pass)

Location: `services/model_armor.py`, the `elif filter_name == "sdp"` branch:

```python
elif filter_name == "sdp" and f_result.sdp_filter_result:
    sdp_res = f_result.sdp_filter_result
    filter_details["sdp"] = {
        "match_state": getattr(sdp_res.match_state, "name", str(sdp_res.match_state))
    }
```

Claim: `SdpFilterResult` is a oneof wrapper around `inspect_result` /
`deidentify_result` / `redact_result` sub-messages, and does not itself carry
a `match_state` field — so `sdp_res.match_state` raises `AttributeError` on
the actual installed client (`google-cloud-modelarmor==0.7.1`), which then
gets caught by the outer `except Exception` and discards the *entire*
inspection result (not just the SDP portion) for any template that has SDP
detection enabled. Please verify the actual `SdpFilterResult` proto shape
against current docs/client source and confirm or refute this.

### Finding C — No per-call timeout (from code-review pass)

`client.sanitize_user_prompt(request=request)` is called with no `timeout`
or `retry` override. Claim: GAPIC-generated defaults for this method are a
60-second timeout with retries on `ServiceUnavailable`. Since this call is
synchronous and sits in the hot path before every Gemini call in a
single-threaded-per-session Streamlit app, an outage or slow response from
Model Armor could stall a participant's turn for up to a minute. Please
verify what the actual default timeout/retry policy is for this method in
the current client library, and whether that's a legitimate operational risk
here.

### Finding D — Logging discards failure detail (from code-review pass)

In `app.py`:

```python
additional_metadata={"model_armor": ma_result} if ma_result.get("inspected") else None
```

Since `inspect_user_prompt` returns `{"inspected": False, ...}` on every
failure path (unconfigured, client-init failure, wrong-endpoint error, SDP
crash, etc.), all of those cases are silently dropped from the structured
`prompts.log` output — the only trace is a `logger.warning` call on a
`model_armor`-named logger that has no handler configured anywhere in the
app (falls through to Python's default stderr lastResort handler). This
combines with Findings A/B: if either is real, the failures they cause would
be invisible in the log file used for post-event analysis. Is this
assessment correct, and is `additional_metadata={"model_armor": ma_result}`
(unconditional) the right fix?

### Finding E — Credentials / IAM for same-project GCE deployment (from doc-verification pass)

Claims, please verify each against current docs:
1. On a GCE VM in the same project as Model Armor, Application Default
   Credentials (no code changes) is sufficient *if and only if* the VM's
   service account has the correct IAM role bound.
2. The correct role name is `roles/modelarmor.user`.
3. The Model Armor API must be separately enabled on the project, via
   `gcloud services enable modelarmor.googleapis.com --project=<project>`.
4. Separately from IAM/API-enablement, this repo's `docker-compose.yml`
   deployment path mounts no credentials and sets no
   `GOOGLE_APPLICATION_CREDENTIALS`, so even with the above configured at
   the project level, the containerized deployment may still fail to
   authenticate unless something else (workload identity, a mounted key,
   metadata-server passthrough) is wired in. Confirm what's actually needed
   for a Docker container running on a GCE VM to inherit the VM's ADC.

### Finding F — Template must pre-exist (from doc-verification pass)

Claim: `sanitize_user_prompt` requires a Model Armor template to already
exist (created via console/gcloud/API) at the `MODEL_ARMOR_LOCATION` before
this code can succeed, and — per this repo's own `DEPLOYMENT_OPS.md` — that
template must have `--template-metadata-log-sanitize-operations` (or its
current equivalent flag name) enabled at creation time for Cloud Logging
audit output to appear. Confirm the current flag/setting name and template
creation requirement.

### Finding G — Other lower-severity/cleanup items flagged (mix of both passes, lower confidence, spend less time here)

- `@lru_cache(maxsize=1)` on `get_model_armor_client` permanently caches a
  failed (`None`) client for the life of the process after any transient
  init failure, with no self-healing/retry.
- `is_model_armor_configured()` is defined but never called anywhere in the
  codebase — dead code duplicating logic already inlined in
  `inspect_user_prompt`. `Optional` is imported but unused.
- Only 4 of the 6 known `filter_results` oneof members are handled
  (`pi_and_jailbreak`, `rai`, `sdp`, `malicious_uris`); `csam` and
  `virus_scan` silently fall through unparsed.
- `.env.example` / `docs/DEPLOYMENT_OPS.md` contain a real-looking internal
  GCP project ID (`virustotal-lab`) as the example value rather than a
  generic placeholder.
- `google-cloud-modelarmor>=0.7.0` — is this pin reasonable, or should it be
  narrowed (e.g. `>=0.7.0,<0.8.0`) given this is a pre-1.0 library, for a
  fixed one-time live event where an unplanned dependency bump the morning
  of the event would be risky?

---

## What's needed back

For each finding (A–G): confirm, refute, or refine it against **current**
official Google Cloud documentation (cite URLs). Resolve Finding A
definitively — it's the one place the two prior passes actually disagreed.
Then give a single prioritized, concrete fix list (code changes + any
`gcloud`/console setup steps) needed before this integration can be trusted
to actually produce working telemetry in `prompts.log` for a live event in
GCP project "A", where the app VM and Model Armor share the same project.
