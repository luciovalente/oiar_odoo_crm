{
    "name": "OIAR Assessment for CRM",
    "version": "18.0.0.0.1.0",
    "category": "Sales/CRM",
    "summary": "Start an Odoo implementation assessment from a CRM lead and get the report back",
    "description": """
OIAR Assessment for CRM
=======================

Starts an Odoo implementation assessment on OIAR from a CRM lead, and attaches the
approved report to the lead.

Requires an external service
----------------------------
This module needs an OIAR account (the assessment runs on the OIAR platform, not in
Odoo) and an API key created there. Nothing is sent until a user presses "Start" on a
lead and confirms. The data sent is shown in the confirmation window: company name,
language, the lead reference, and, when filled, industry, company size, current
systems, desired timeline, the lead tags (as Odoo apps of interest) and the lead
internal notes (as problems to solve). No other data leaves Odoo.

OIAR sends back, to the webhook of this module, the approved report of the project
started from the lead. The webhook accepts only requests signed with the shared
secret.
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
