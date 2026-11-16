import logging

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

from .. import tools
from .oiar_client import PARAM, OiarClient, OiarError

_logger = logging.getLogger(__name__)

FINAL_STATUSES = ("completed", "cancelled", "error")


class CrmLead(models.Model):
    _inherit = "crm.lead"

    oiar_project_id = fields.Char(string="OIAR project", copy=False, readonly=True, index=True)
    oiar_status = fields.Selection(
        [
            ("created", "Created"),
            ("planning", "Planning"),
            ("interviewing", "Interviewing"),
            ("analyzing", "Analyzing"),
            ("reporting", "Reporting"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("error", "Error"),
            ("suspended", "Suspended"),
        ],
        string="OIAR status",
        copy=False,
        readonly=True,
    )
    oiar_project_url = fields.Char(string="OIAR link", compute="_compute_oiar_project_url")
    # What the client told us, sent to OIAR as the scenario's input. The orchestrator
    # reads it as data and does not ask the client again.
    oiar_industry = fields.Char(string="Industry and main activity")
    oiar_company_size = fields.Selection(
        [(size, size) for size in tools.COMPANY_SIZES], string="Number of employees"
    )
    oiar_current_systems = fields.Text(string="Systems used today")
    oiar_target_timeline = fields.Char(string="Desired timeline")

    @api.depends("oiar_project_id")
    def _compute_oiar_project_url(self):
        portal = (self.env["ir.config_parameter"].sudo().get_param(PARAM + "portal_url") or "").rstrip("/")
        for lead in self:
            lead.oiar_project_url = f"{portal}/projects/{lead.oiar_project_id}" if portal and lead.oiar_project_id else False

    # ------------------------------------------------------------------ outbound

    def _oiar_external_ref(self):
        self.ensure_one()
        return f"{self.env['ir.config_parameter'].sudo().get_param('database.uuid')}:{self.id}"

    def _oiar_company_name(self):
        self.ensure_one()
        return (self.partner_id.commercial_partner_id.name or self.partner_name or "").strip()

    def _oiar_scenario_inputs(self):
        self.ensure_one()
        industry = self.oiar_industry or self.partner_id.commercial_partner_id.industry_id.name
        return tools.build_scenario_inputs(
            industry=industry,
            company_size=self.oiar_company_size,
            current_systems=self.oiar_current_systems,
            apps=self.tag_ids.mapped("name"),
            pain_points=html2plaintext(self.description or ""),
            target_timeline=self.oiar_target_timeline,
        )

    def _oiar_payload(self):
        self.ensure_one()
        company = self._oiar_company_name()
        if not company:
            raise UserError(self.env._("Set the customer (or the company name) on the lead first."))
        get = self.env["ir.config_parameter"].sudo().get_param
        payload = {
            "name": f"{company} - {self.name}"[:200],
            "company_name": company,
            "scenario": get(PARAM + "scenario") or "odoo-implementation-assessment",
            "language": tools.project_language(self.partner_id.lang or self.env.user.lang),
            "external_ref": self._oiar_external_ref(),
        }
        connector = get(PARAM + "dataroom_connector_id")
        if connector:
            payload["dataroom_connector_id"] = connector
        inputs = self._oiar_scenario_inputs()
        if inputs:
            payload["scenario_inputs"] = inputs
        return payload

    def action_oiar_start(self):
        self.ensure_one()
        if self.oiar_project_id:
            raise UserError(self.env._("An OIAR assessment is already linked to this lead."))
        wizard = self.env["oiar.assessment.wizard"].create({"lead_id": self.id})
        return {
            "type": "ir.actions.act_window",
            "res_model": "oiar.assessment.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
            "name": self.env._("Start OIAR assessment"),
        }

    def _oiar_create_project(self):
        self.ensure_one()
        if self.oiar_project_id:
            raise UserError(self.env._("An OIAR assessment is already linked to this lead."))
        project = OiarClient.from_env(self.env).create_project(self._oiar_payload())
        self.write({"oiar_project_id": project["id"], "oiar_status": project.get("status") or "created"})
        self.message_post(
            body=Markup(escape(self.env._("OIAR assessment started (project %s).", project["id"]))),
        )
        return project

    def action_oiar_refresh_status(self):
        for lead in self.filtered("oiar_project_id"):
            lead._oiar_refresh_status()
        return True

    def _oiar_refresh_status(self):
        self.ensure_one()
        data = OiarClient.from_env(self.env).project_status(self.oiar_project_id)
        status = data.get("project_status")
        if status and status != self.oiar_status:
            self.oiar_status = status

    @api.model
    def _cron_oiar_refresh_status(self):
        leads = self.search(
            [("oiar_project_id", "!=", False), ("oiar_status", "not in", list(FINAL_STATUSES))]
        )
        for lead in leads:
            try:
                with self.env.cr.savepoint():
                    lead._oiar_refresh_status()
            except OiarError as exc:
                # One unreachable project must not stop the others, and a missing
                # configuration is not an error worth a traceback every half hour.
                _logger.info("OIAR status of lead %s not refreshed: %s", lead.id, exc)
                if "not configured" in str(exc):
                    break

    # ------------------------------------------------------------------- inbound

    def _oiar_handle_report(self, event):
        """The signed ``report.approved`` event of this lead's project."""
        self.ensure_one()
        data = event.get("data") or {}
        report = data.get("report") or {}
        project = data.get("project") or {}
        content = report.get("content") or ""

        project_id = project.get("id") or self.oiar_project_id
        if project_id and not self.oiar_project_id:
            self.oiar_project_id = project_id
        self.oiar_status = "completed"

        attachments = self.env["ir.attachment"]
        name = f"OIAR assessment - {self._oiar_company_name() or self.name}"
        if content:
            attachments |= self.env["ir.attachment"].create(
                {
                    "name": f"{name}.md",
                    "raw": content.encode(),
                    "mimetype": "text/markdown",
                    "res_model": "crm.lead",
                    "res_id": self.id,
                }
            )
        pdf = self._oiar_try_pdf()
        if pdf:
            attachments |= self.env["ir.attachment"].create(
                {
                    "name": f"{name}.pdf",
                    "raw": pdf,
                    "mimetype": "application/pdf",
                    "res_model": "crm.lead",
                    "res_id": self.id,
                }
            )
        # The report is text written from what external people answered: it is
        # attached as a file, never rendered as HTML in the chatter.
        self.message_post(
            body=Markup(escape(self.env._("The OIAR assessment report is ready and attached."))),
            attachment_ids=attachments.ids,
            author_id=self.env.ref("base.partner_root").id,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            summary=self.env._("OIAR report ready: prepare the proposal"),
            user_id=(self.user_id or self.create_uid).id,
        )
        stage_id = int(self.env["ir.config_parameter"].sudo().get_param(PARAM + "report_stage_id") or 0)
        stage = self.env["crm.stage"].browse(stage_id).exists()
        if stage:
            self.stage_id = stage

    def _oiar_try_pdf(self):
        """The PDF of the report, or None: the markdown is already attached either way."""
        try:
            return OiarClient.from_env(self.env).download_report_pdf(self.oiar_project_id)
        except UserError as exc:
            _logger.info("OIAR PDF of lead %s not downloaded: %s", self.id, exc)
            return None
