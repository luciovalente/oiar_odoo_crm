import logging

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PARAM = "oiar_crm_assessment."
TIMEOUT = 20


class OiarError(UserError):
    """The OIAR call failed. The message never contains the API key."""


class OiarClient:
    """Thin HTTP client of the OIAR API. Authenticates with an ``oiar_pk_`` key."""

    def __init__(self, base_url, api_key):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""

    @classmethod
    def from_env(cls, env):
        get = env["ir.config_parameter"].sudo().get_param
        client = cls(get(PARAM + "base_url"), get(PARAM + "api_key"))
        if not client.base_url or not client.api_key:
            raise OiarError(_("OIAR is not configured: set the URL and the API key in the CRM settings."))
        return client

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method,
                url,
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
                timeout=TIMEOUT,
                allow_redirects=False,
                **kwargs,
            )
        except requests.RequestException as exc:
            _logger.warning("OIAR %s %s failed: %s", method, path, type(exc).__name__)
            raise OiarError(_("OIAR is not reachable (%s).", type(exc).__name__)) from None
        if response.status_code in (401, 403):
            raise OiarError(_("OIAR refused the API key (HTTP %s).", response.status_code))
        if response.status_code >= 400:
            detail = ""
            try:
                detail = str(response.json().get("detail", ""))[:300]
            except ValueError:
                pass
            raise OiarError(_("OIAR answered HTTP %(code)s. %(detail)s", code=response.status_code, detail=detail))
        return response

    def check(self):
        self._request("GET", "/projects/")
        return True

    def create_project(self, payload):
        return self._request("POST", "/projects/", json=payload).json()

    def project_status(self, project_id):
        return self._request("GET", f"/projects/{project_id}/status").json()

    def download_report_pdf(self, project_id):
        return self._request("GET", f"/projects/{project_id}/reports/index/download-pdf").content
