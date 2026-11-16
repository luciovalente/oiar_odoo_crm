# oiar_odoo_crm

Odoo module `oiar_crm_assessment`: start an [OIAR](https://oiarplatform.com) Odoo implementation
assessment from a CRM lead and get the approved report back on the lead.

Odoo 18 (branch `18.0`). License LGPL-3.

## How it works

1. **Settings → CRM → OIAR Assessment**: API URL, API key (`oiar_pk_...`, created in the OIAR portal),
   Data Room connector id, optional portal URL, report stage.
2. **Lead → "Start OIAR assessment"**: a wizard shows the exact JSON sent to OIAR and asks to confirm
   that the customer is informed. The project is created with `external_ref = <database uuid>:<lead id>`.
   Sent: company, language, and the scenario inputs the lead already holds (industry, size, systems,
   timeline, tags as Odoo apps of interest, internal notes as pain points).
3. **Webhook**: in OIAR set the account's report webhook to `https://<your odoo>/oiar/webhook`
   (shown in the settings) and paste the secret in the settings. On `report.approved` the report is
   attached to the lead (Markdown, plus PDF when downloadable), a chatter note is posted, an activity is
   scheduled for the salesperson and the lead optionally moves to a stage.
4. **Status**: a cron (30 min) and a button refresh the assessment status on the lead.

## Security

* The webhook verifies `X-OIAR-Signature` (HMAC-SHA256 of `"<t>.<raw body>"`, 5 minute window) and drops
  repeated `X-OIAR-Delivery` ids.
* The report is text derived from what external stakeholders answered: it is attached as a file, never
  rendered as HTML.
* The API key and the webhook secret are stored in `ir.config_parameter` (readable by administrators only).
* With several databases on one Odoo, the webhook needs the database to be resolved (`dbfilter` or `?db=`).
* The webhook URL must be reachable from OIAR over https.

## Tests

```bash
python -m unittest discover -s tests_standalone      # no Odoo needed: signature, input mapping
odoo -d test -i oiar_crm_assessment --test-tags /oiar_crm_assessment --stop-after-init   # Odoo tests
```

## Limits (v1)

Not done: stakeholders invitation from Odoo, Fit-Gap Register to quotation lines (needs structured
output from OIAR), embedded interview. The Odoo test suite and the views were written against Odoo 18
but not executed on a running instance in the session that produced them.
