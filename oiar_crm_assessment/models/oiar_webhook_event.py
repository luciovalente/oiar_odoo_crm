from odoo import fields, models


class OiarWebhookEvent(models.Model):
    """Deliveries already handled: OIAR resends the same ``X-OIAR-Delivery`` on a retry."""

    _name = "oiar.webhook.event"
    _description = "OIAR webhook delivery"
    _order = "id desc"

    delivery_id = fields.Char(required=True, index=True)
    event_type = fields.Char()
    lead_id = fields.Many2one("crm.lead", ondelete="set null")

    _delivery_uniq = models.Constraint("unique(delivery_id)", "Delivery already handled.")
