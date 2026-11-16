import json
import logging

from psycopg2 import IntegrityError

from odoo import http
from odoo.http import request

from .. import tools

_logger = logging.getLogger(__name__)

PARAM = "oiar_crm_assessment."


class OiarWebhook(http.Controller):
    @http.route("/oiar/webhook", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def webhook(self, **_kwargs):
        env = request.env
        body = request.httprequest.get_data()
        secret = env["ir.config_parameter"].sudo().get_param(PARAM + "webhook_secret")
        if not tools.verify_signature(secret, body, request.httprequest.headers.get("X-OIAR-Signature")):
            _logger.warning("OIAR webhook: signature rejected")
            return request.make_json_response({"error": "invalid signature"}, status=401)
        try:
            event = json.loads(body)
        except ValueError:
            return request.make_json_response({"error": "invalid body"}, status=400)

        event_type = event.get("type")
        if event_type == "ping":
            return request.make_json_response({"status": "pong"})
        if event_type != "report.approved":
            return request.make_json_response({"status": "ignored"})

        db_uuid, lead_id = tools.parse_external_ref((event.get("data") or {}).get("project", {}).get("external_ref"))
        if db_uuid != env["ir.config_parameter"].sudo().get_param("database.uuid"):
            # Another database's lead, or a project not started from this CRM: nothing to retry.
            return request.make_json_response({"status": "ignored"})
        lead = env["crm.lead"].sudo().browse(lead_id).exists()
        if not lead:
            return request.make_json_response({"status": "ignored"})

        delivery = request.httprequest.headers.get("X-OIAR-Delivery") or event.get("id")
        events = env["oiar.webhook.event"].sudo()
        try:
            with env.cr.savepoint():
                events.create({"delivery_id": delivery, "event_type": event_type, "lead_id": lead.id})
        except IntegrityError:
            return request.make_json_response({"status": "duplicate"})
        lead._oiar_handle_report(event)
        return request.make_json_response({"status": "ok"})
