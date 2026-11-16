from odoo import _, fields, models

from .oiar_client import OiarClient


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oiar_base_url = fields.Char(
        string="OIAR API URL",
        config_parameter="oiar_crm_assessment.base_url",
        help="Address of the OIAR API, e.g. https://api.oiarplatform.com",
    )
    oiar_api_key = fields.Char(
        string="OIAR API key",
        config_parameter="oiar_crm_assessment.api_key",
        help="Key created in the OIAR portal (starts with oiar_pk_). The account that owns it owns the projects.",
    )
    oiar_webhook_secret = fields.Char(
        string="Webhook secret",
        config_parameter="oiar_crm_assessment.webhook_secret",
        help="The secret OIAR shows when you set the report webhook (starts with whsec_).",
    )
    oiar_portal_url = fields.Char(
        string="OIAR portal URL",
        config_parameter="oiar_crm_assessment.portal_url",
        help="Optional. Used for the link to the project on the lead.",
    )
    oiar_scenario = fields.Char(
        string="Scenario",
        config_parameter="oiar_crm_assessment.scenario",
        default="odoo-implementation-assessment",
    )
    oiar_dataroom_connector_id = fields.Char(
        string="Data Room connector",
        config_parameter="oiar_crm_assessment.dataroom_connector_id",
        help="Id of the OIAR Data Room connector where the projects are stored (required by OIAR in production).",
    )
    oiar_report_stage_id = fields.Many2one(
        "crm.stage",
        string="Stage when the report arrives",
        config_parameter="oiar_crm_assessment.report_stage_id",
        help="Optional. The lead moves to this stage when the approved report arrives.",
    )
    oiar_webhook_url = fields.Char(string="Webhook URL", compute="_compute_oiar_webhook_url")

    def _compute_oiar_webhook_url(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        for record in self:
            record.oiar_webhook_url = f"{base.rstrip('/')}/oiar/webhook"

    def action_oiar_test_connection(self):
        self.ensure_one()
        OiarClient.from_env(self.env).check()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OIAR"),
                "message": _("Connection OK."),
                "type": "success",
                "sticky": False,
            },
        }
