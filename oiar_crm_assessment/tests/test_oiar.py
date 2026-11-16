import json
import time
from unittest.mock import MagicMock, patch

from odoo.tests import HttpCase, TransactionCase, tagged

from .. import tools

SECRET = "whsec_test"


def _event(lead, delivery="d1"):
    return {
        "id": delivery,
        "type": "report.approved",
        "data": {
            "project": {"id": "p-1", "external_ref": lead._oiar_external_ref()},
            "report": {"format": "markdown", "content": "# Report\n<script>x</script>"},
        },
    }


@tagged("post_install", "-at_install")
class TestOiarLead(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        params = cls.env["ir.config_parameter"].sudo()
        params.set_param("oiar_crm_assessment.base_url", "https://oiar.example")
        params.set_param("oiar_crm_assessment.api_key", "oiar_pk_test")
        cls.partner = cls.env["res.partner"].create({"name": "Acme Srl", "lang": "it_IT"})
        cls.lead = cls.env["crm.lead"].create(
            {"name": "ERP", "partner_id": cls.partner.id, "oiar_company_size": "11-50", "oiar_industry": "Metalmeccanica"}
        )

    def test_payload(self):
        payload = self.lead._oiar_payload()
        self.assertEqual(payload["language"], "it_IT")
        self.assertEqual(payload["company_name"], "Acme Srl")
        self.assertEqual(payload["external_ref"], self.lead._oiar_external_ref())
        self.assertEqual(payload["scenario_inputs"]["company_size"], "11-50")

    def test_create_project_once(self):
        response = MagicMock(status_code=201)
        response.json.return_value = {"id": "p-1", "status": "created"}
        with patch("requests.request", return_value=response) as request:
            self.lead._oiar_create_project()
        self.assertEqual(self.lead.oiar_project_id, "p-1")
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer oiar_pk_test")
        with self.assertRaises(Exception):
            self.lead._oiar_create_project()

    def test_report_attached_as_file(self):
        self.lead.oiar_project_id = "p-1"
        with patch.object(type(self.lead), "_oiar_try_pdf", return_value=None):
            self.lead._oiar_handle_report(_event(self.lead))
        self.assertEqual(self.lead.oiar_status, "completed")
        attachment = self.env["ir.attachment"].search([("res_model", "=", "crm.lead"), ("res_id", "=", self.lead.id)])
        self.assertEqual(len(attachment), 1)
        self.assertIn(b"<script>", attachment.raw)  # kept as file content, never as chatter HTML
        self.assertNotIn("<script>", self.lead.message_ids[0].body)


@tagged("post_install", "-at_install")
class TestOiarWebhook(HttpCase):
    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param("oiar_crm_assessment.webhook_secret", SECRET)
        self.lead = self.env["crm.lead"].create({"name": "ERP"})
        self.env.cr.flush()

    def _post(self, event, secret=SECRET, stamp=None):
        body = json.dumps(event).encode()
        headers = {
            "X-OIAR-Signature": tools.sign(secret, body, stamp or time.time()),
            "X-OIAR-Delivery": event["id"],
            "Content-Type": "application/json",
        }
        return self.url_open("/oiar/webhook", data=body, headers=headers)

    def test_bad_signature(self):
        self.assertEqual(self._post(_event(self.lead), secret="wrong").status_code, 401)

    def test_stale_signature(self):
        self.assertEqual(self._post(_event(self.lead), stamp=time.time() - 3600).status_code, 401)

    def test_ping(self):
        self.assertEqual(self._post({"id": "p", "type": "ping", "data": {}}).json()["status"], "pong")

    def test_duplicate_delivery_is_handled_once(self):
        with patch.object(type(self.env["crm.lead"]), "_oiar_try_pdf", return_value=None):
            self.assertEqual(self._post(_event(self.lead)).json()["status"], "ok")
            self.assertEqual(self._post(_event(self.lead)).json()["status"], "duplicate")
