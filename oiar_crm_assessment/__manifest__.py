{
    "name": "OIAR Assessment for CRM",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Start an OIAR Odoo implementation assessment from a CRM lead "
    "and get the approved report back on the lead",
    "description": """
Connects the CRM to OIAR (oiarplatform.com).

* "Start OIAR assessment" button on the lead: creates the project on OIAR with the
  lead as external reference and the data the lead already holds.
* Signed webhook: when the report is approved in OIAR it is attached to the lead,
  announced in the chatter and a follow-up activity is scheduled.
* Status of the assessment refreshed on the lead.
    """,
    "author": "Lucio Valente",
    "website": "https://oiarplatform.com",
    "license": "LGPL-3",
    "depends": ["crm", "mail"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/res_config_settings_views.xml",
        "views/crm_lead_views.xml",
        "wizards/oiar_assessment_wizard_views.xml",
    ],
    "images": ["static/description/banner.png"],
    "application": False,
    "installable": True,
}
