"""Run without Odoo: ``python -m unittest discover -s tests_standalone``."""

import importlib.util
import pathlib
import time
import unittest

_spec = importlib.util.spec_from_file_location(
    "oiar_tools", pathlib.Path(__file__).parent.parent / "oiar_crm_assessment" / "tools.py"
)
tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tools)

BODY = b'{"id":"d1","type":"report.approved"}'


class TestSignature(unittest.TestCase):
    def test_roundtrip(self):
        header = tools.sign("whsec_x", BODY, time.time())
        self.assertTrue(tools.verify_signature("whsec_x", BODY, header))

    def test_vector_from_oiar_platform(self):
        # Computed with sign() of oiar_platform services/report_webhook.py.
        self.assertEqual(
            tools.sign("whsec_x", BODY, 1700000000),
            "t=1700000000,v1=5d9d16c14aaf92221eebcfe4cd01fd6f993c0d93cbe968fc125387b77b999770",
        )
        self.assertTrue(
            tools.verify_signature(
                "whsec_x",
                BODY,
                "t=1700000000,v1=5d9d16c14aaf92221eebcfe4cd01fd6f993c0d93cbe968fc125387b77b999770",
                now=1700000100,
            )
        )

    def test_rejections(self):
        good = tools.sign("whsec_x", BODY, time.time())
        self.assertFalse(tools.verify_signature("whsec_y", BODY, good))
        self.assertFalse(tools.verify_signature("whsec_x", BODY + b" ", good))
        self.assertFalse(tools.verify_signature("whsec_x", BODY, tools.sign("whsec_x", BODY, time.time() - 3600)))
        self.assertFalse(tools.verify_signature("whsec_x", BODY, ""))
        self.assertFalse(tools.verify_signature("whsec_x", BODY, "garbage"))
        self.assertFalse(tools.verify_signature("", BODY, good))


class TestInputs(unittest.TestCase):
    def test_empty_values_left_out(self):
        self.assertEqual(tools.build_scenario_inputs(industry="  ", company_size="x"), {})

    def test_clipping_and_apps(self):
        out = tools.build_scenario_inputs(
            industry="a" * 500, apps=["CRM", "CRM", "x" * 300] + [str(i) for i in range(40)], pain_points="p" * 5000
        )
        self.assertEqual(len(out["industry"]), 300)
        self.assertEqual(out["odoo_apps_of_interest"][0], "CRM")
        self.assertEqual(len(out["odoo_apps_of_interest"]), 20)
        self.assertTrue(all(len(a) <= 100 for a in out["odoo_apps_of_interest"]))
        self.assertEqual(len(out["main_pain_points"]), 2000)

    def test_language_and_ref(self):
        self.assertEqual(tools.project_language("it_IT"), "it_IT")
        self.assertEqual(tools.project_language("es_MX"), "es_ES")
        self.assertEqual(tools.project_language("fr_FR"), "en_EN")
        self.assertEqual(tools.parse_external_ref("uuid-1:42"), ("uuid-1", 42))
        self.assertEqual(tools.parse_external_ref("nope"), (None, None))


if __name__ == "__main__":
    unittest.main()
