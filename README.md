# OIAR Assessment for CRM

Odoo module `oiar_crm_assessment`. It connects the Odoo CRM to [OIAR](https://oiarplatform.com):
you start an Odoo implementation assessment from a lead, the customer is interviewed on OIAR,
and the approved report comes back and is attached to the lead.

License: LGPL-3. Status: beta (`x.0.0.1.0`), see [Limits](#limits).

## What it is for

A consultancy that sells Odoo implementations needs to understand the customer's processes before
quoting. OIAR runs that assessment (interviews with the customer's people, analysis, report). This
module removes the copy and paste between the two: the lead already holds who the customer is and
what they asked for, so the assessment starts from there, and the report ends up where the salesperson
works.

```
Odoo lead ── "Start OIAR assessment" ──▶ OIAR project (external ref = the lead)
                                              │ interviews, analysis, report, owner approves
Odoo lead ◀── signed webhook "report.approved" ┘
   report attached · note in chatter · activity for the salesperson · optional stage change
```

## What you need

* An OIAR account with full platform access, and an API key created in the OIAR portal (`oiar_pk_...`).
* The id of the OIAR Data Room connector where the projects are stored (OIAR requires it in production).
* Odoo 17.0, 18.0, 19.0 or 20.0 (one branch per version), with the `crm` and `mail` apps.
* Odoo.sh or on-premise. **Odoo Online does not allow custom modules**, so it cannot be used there.
* A public HTTPS address for your Odoo: OIAR calls it to deliver the report. Behind a VPN or firewall the
  report cannot arrive (the status refresh still works).
* The Python package `requests` (already present in every standard Odoo installation).

## Install

1. Take the branch that matches your Odoo version (`17.0`, `18.0`, `19.0`, `20.0`) and copy the folder
   `oiar_crm_assessment` into a directory of your `addons_path`.

   ```bash
   git clone --branch 18.0 --depth 1 https://github.com/luciovalente/oiar_odoo_crm.git
   cp -r oiar_odoo_crm/oiar_crm_assessment /path/to/your/addons/
   ```
2. Restart Odoo, enable the developer mode, **Apps → Update Apps List**.
3. Search "OIAR Assessment for CRM" and install it.

## Configure

**On OIAR**

1. In the portal create an API key (the account that owns it owns the projects). Copy it: it is shown once.
2. Note the id of the Data Room connector the projects must use.
3. After step 2 below in Odoo, register the webhook (the settings page shows the exact URL):

   ```bash
   curl -X PUT https://<oiar api>/auth/me/report-webhook \
     -H "Authorization: Bearer <jwt of your account>" -H "Content-Type: application/json" \
     -d '{"url": "https://<your odoo>/oiar/webhook"}'
   ```

   The answer contains the signing secret (`whsec_...`), shown only once. `POST /auth/me/report-webhook/test`
   sends a signed test event.

**In Odoo** (Settings → CRM → OIAR Assessment)

| Setting | What to put |
|---|---|
| OIAR API URL | The address of the OIAR API |
| OIAR API key | The `oiar_pk_...` key |
| OIAR portal URL | Optional: gives the lead a link to the project |
| Scenario | `odoo-implementation-assessment` (default) |
| Data Room connector | The connector id from OIAR |
| Webhook secret | The `whsec_...` secret |
| Stage when the report arrives | Optional: the lead moves there automatically |

Use **Test connection** after saving. The API key and the secret are stored as system parameters,
readable by administrators only.

With several databases on one Odoo server, the webhook must be able to choose the database
(`dbfilter`, or add `?db=<name>` to the URL you register).

## Use

1. Open a lead. Fill the **OIAR Assessment** tab with what you know: industry, company size, systems used
   today, desired timeline. Put the Odoo apps of interest in the **tags** and the customer's problems in the
   **internal notes**.
2. Press **Start OIAR assessment**. A window shows the exact data that will be sent. Confirm that the customer
   is informed, then **Start**. The lead now carries the OIAR project and its status.
3. The assessment proceeds on OIAR (the customer is interviewed there). The status on the lead is refreshed
   every 30 minutes and with **Refresh OIAR status**.
4. When the report is approved on OIAR, the lead receives it (Markdown, plus PDF when available), a note in the
   chatter, and an activity for the salesperson: *OIAR report ready: prepare the proposal*.

What is sent to OIAR:

| From the lead | Sent as |
|---|---|
| Customer (or company name) | company name |
| Customer language (Italian, Spanish, otherwise English) | project language |
| Lead id and database | opaque reference, returned with the report |
| Industry, company size, systems, timeline (tab) | scenario inputs |
| Tags | Odoo apps of interest |
| Internal notes | main problems to solve |

Over-long values are trimmed to the limits the scenario declares. Empty fields are not sent.

## Data and security

* Nothing is sent before a user confirms in the window; the data shown there is all that is sent.
* The webhook accepts a request only with a valid `X-OIAR-Signature` (HMAC-SHA256, 5 minute window) and
  handles a repeated `X-OIAR-Delivery` once.
* The report is text derived from what external people answered. It is attached as a file and never
  rendered as HTML.
* The module needs no activation key. Your leads stay in Odoo; the assessment data lives on OIAR.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "OIAR refused the API key" | Wrong or revoked key, or the account lacks full platform access |
| Start fails with HTTP 422 | A value the scenario does not accept; the message says which |
| The report never arrives | Webhook not registered, wrong secret (Odoo logs "signature rejected"), Odoo not reachable over HTTPS, or the project was not started from this database |
| The lead is not found | The project was started from another database: the reference carries the database uuid |

## Versions

| Branch | Odoo |
|---|---|
| `17.0` | 17.0 |
| `18.0` | 18.0 |
| `19.0` | 19.0 |
| `20.0` | 20.0 |

The module has the same name in every branch, and the version is `<odoo>.<major>.<minor>.<bugfix>`.

## Development

```bash
python -m unittest discover -s tests_standalone     # no Odoo needed: signature, input mapping
odoo -d test -i oiar_crm_assessment --test-tags /oiar_crm_assessment --stop-after-init
```

## Limits

* Beta. The Odoo tests and the views were written against each Odoo version but not run on a live instance
  by the author of this first release: run them before relying on it.
* Not included: inviting the customer's people to the interviews from Odoo, turning the Fit-Gap Register
  into quotation lines (needs structured output from OIAR), embedding the interview in Odoo.
