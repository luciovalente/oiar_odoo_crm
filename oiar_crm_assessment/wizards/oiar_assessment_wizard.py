import json

from odoo import api, fields, models
from odoo.exceptions import UserError


class OiarAssessmentWizard(models.TransientModel):
    _name = "oiar.assessment.wizard"
    _description = "Start an OIAR assessment"

    lead_id = fields.Many2one("crm.lead", required=True, ondelete="cascade")
    preview = fields.Text(string="Data sent to OIAR", compute="_compute_preview")
    confirmed = fields.Boolean(
        string="The customer knows their answers are processed by OIAR",
        help="The data above leaves Odoo for OIAR, which is an external service.",
    )

    @api.depends("lead_id")
    def _compute_preview(self):
        for wizard in self:
            try:
                payload = wizard.lead_id._oiar_payload()
                wizard.preview = json.dumps(payload, indent=2, ensure_ascii=False)
            except UserError as exc:
                wizard.preview = str(exc)

    def action_start(self):
        self.ensure_one()
        if not self.confirmed:
            raise UserError(self.env._("Confirm that the customer is informed before starting."))
        self.lead_id._oiar_create_project()
        return {"type": "ir.actions.act_window_close"}
