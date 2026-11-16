"""Pure helpers, no Odoo import: they are tested without an Odoo server.

The signature format is the one of OIAR's ``services/report_webhook.py``:
``X-OIAR-Signature: t=<unix seconds>,v1=<hex HMAC-SHA256 of "<t>.<raw body>">``.
"""

import hashlib
import hmac
import time

SIGNATURE_TOLERANCE_SECONDS = 300

# Limits declared by the scenario `odoo-implementation-assessment` (scenario.yaml).
COMPANY_SIZES = ("1-10", "11-50", "51-250", "251-1000", "1000+")
LIMITS = {
    "industry": 300,
    "current_systems": 1000,
    "main_pain_points": 2000,
    "target_timeline": 200,
    "app_item": 100,
    "apps_max_items": 20,
}


def sign(secret, body, timestamp):
    mac = hmac.new(secret.encode(), f"{int(timestamp)}.".encode() + body, hashlib.sha256)
    return f"t={int(timestamp)},v1={mac.hexdigest()}"


def verify_signature(secret, body, header, now=None, tolerance=SIGNATURE_TOLERANCE_SECONDS):
    """True only for a well-formed, recent signature made with ``secret`` over ``body``."""
    if not secret or not header:
        return False
    parts = {}
    for chunk in header.split(","):
        key, sep, value = chunk.strip().partition("=")
        if sep:
            parts[key] = value
    try:
        timestamp = int(parts["t"])
        received = parts["v1"]
    except (KeyError, ValueError):
        return False
    if abs((time.time() if now is None else now) - timestamp) > tolerance:
        return False
    expected = sign(secret, body, timestamp).split("v1=", 1)[1]
    return hmac.compare_digest(expected, received)


def _clip(text, limit):
    text = " ".join((text or "").split())
    return text[:limit]


def build_scenario_inputs(
    industry=None,
    company_size=None,
    current_systems=None,
    apps=None,
    pain_points=None,
    target_timeline=None,
):
    """The ``scenario_inputs`` of ``POST /projects/``: empty values are left out, the
    rest is clipped to what the scenario declares (an over-long value is a 422)."""
    inputs = {}
    if industry and industry.strip():
        inputs["industry"] = _clip(industry, LIMITS["industry"])
    if company_size in COMPANY_SIZES:
        inputs["company_size"] = company_size
    if current_systems and current_systems.strip():
        inputs["current_systems"] = _clip(current_systems, LIMITS["current_systems"])
    clean_apps = []
    for app in apps or []:
        item = _clip(app, LIMITS["app_item"])
        if item and item not in clean_apps:
            clean_apps.append(item)
    if clean_apps:
        inputs["odoo_apps_of_interest"] = clean_apps[: LIMITS["apps_max_items"]]
    if pain_points and pain_points.strip():
        # newlines carry meaning in a description: keep them, clip only the length
        inputs["main_pain_points"] = pain_points.strip()[: LIMITS["main_pain_points"]]
    if target_timeline and target_timeline.strip():
        inputs["target_timeline"] = _clip(target_timeline, LIMITS["target_timeline"])
    return inputs


def project_language(odoo_lang):
    code = (odoo_lang or "").lower()
    if code.startswith("it"):
        return "it_IT"
    if code.startswith("es"):
        return "es_ES"
    return "en_EN"


def parse_external_ref(ref):
    """``"<database uuid>:<lead id>"`` -> (uuid, id), or (None, None)."""
    db_uuid, sep, lead_id = (ref or "").rpartition(":")
    if not sep or not db_uuid or not lead_id.isdigit():
        return None, None
    return db_uuid, int(lead_id)
