import os
import logging
from typing import Dict, Any

logger = logging.getLogger("model_armor")

_CLIENT_CACHE: Dict[str, Any] = {}

def get_model_armor_client(location: str):
    """Initializes and caches the Model Armor client for the specified location."""
    if not location or location == "global":
        location = "us-central1"

    if location in _CLIENT_CACHE:
        return _CLIENT_CACHE[location]

    try:
        from google.cloud import modelarmor_v1
        from google.api_core.client_options import ClientOptions

        endpoint = f"modelarmor.{location}.rep.googleapis.com"
        client = modelarmor_v1.ModelArmorClient(
            client_options=ClientOptions(api_endpoint=endpoint)
        )
        _CLIENT_CACHE[location] = client
        return client
    except Exception as e:
        logger.warning(f"Failed to initialize ModelArmorClient: {e}")
        return None

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

        response = client.sanitize_user_prompt(request=request, timeout=2.0)
        sanitization_result = response.sanitization_result

        # Parse match state
        match_state_name = getattr(sanitization_result.filter_match_state, "name", str(sanitization_result.filter_match_state))
        invocation_result_name = getattr(sanitization_result.invocation_result, "name", str(sanitization_result.invocation_result))
        is_match = match_state_name == "MATCH_FOUND"

        filter_details = {}
        injection_detected = False
        injection_confidence = "UNSPECIFIED"

        for filter_name, f_result in sanitization_result.filter_results.items():
            # Check prompt injection and jailbreak results
            if filter_name == "pi_and_jailbreak" and f_result.pi_and_jailbreak_filter_result:
                pi_res = f_result.pi_and_jailbreak_filter_result
                pi_match = getattr(pi_res.match_state, "name", str(pi_res.match_state))
                pi_conf = getattr(pi_res.confidence_level, "name", str(pi_res.confidence_level))
                if pi_match == "MATCH_FOUND":
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
                sub_res = (
                    getattr(sdp_res, "inspect_result", None)
                    or getattr(sdp_res, "deidentify_result", None)
                    or getattr(sdp_res, "redact_result", None)
                )
                m_state = getattr(sub_res.match_state, "name", str(sub_res.match_state)) if sub_res and hasattr(sub_res, "match_state") else "MATCH_STATE_UNSPECIFIED"
                filter_details["sdp"] = {
                    "match_state": m_state
                }
            elif filter_name == "malicious_uris" and f_result.malicious_uri_filter_result:
                uri_res = f_result.malicious_uri_filter_result
                filter_details["malicious_uris"] = {
                    "match_state": getattr(uri_res.match_state, "name", str(uri_res.match_state))
                }
            elif filter_name == "csam" and getattr(f_result, "csam_filter_filter_result", None):
                csam_res = f_result.csam_filter_filter_result
                filter_details["csam"] = {
                    "match_state": getattr(csam_res.match_state, "name", str(csam_res.match_state))
                }
            elif filter_name == "virus_scan" and getattr(f_result, "virus_scan_filter_result", None):
                vs_res = f_result.virus_scan_filter_result
                filter_details["virus_scan"] = {
                    "match_state": getattr(vs_res.match_state, "name", str(vs_res.match_state))
                }
            else:
                # Generic fallback for any other or future filters
                filter_details[filter_name] = {"raw_result": str(f_result)}

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
