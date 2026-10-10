"""Connected scheduled-service coverage without inventing a service slot."""

import os
import unittest

try:
    import psycopg
except ImportError:
    psycopg = None

if psycopg is not None:
    from psycopg.types.json import Jsonb
    from phase1c_reader import read_run
    from phase1c_deal_decision import assemble_deal_decision


RUN_ID = "00000000-0000-4000-8000-000000260001"


@unittest.skipUnless(psycopg is not None and os.environ.get("DATABASE_URL"),
                     "PostgreSQL integration requires psycopg and DATABASE_URL")
class ServicePilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg.connect(os.environ["DATABASE_URL"])
        cls.conn.execute("SET search_path TO deal_desk, public")
        try:
            cls.conn.execute("""INSERT INTO products (product_id, product_code, catalog_version,
                product_name, category, product_type, attributes_json, list_price, standard_cost,
                billing_model, unit_of_measure, is_sellable, fulfillment_mode, stock_uom)
                VALUES ('PILOT-SERVICE', 'PILOT-SERVICE', 'CATALOGUE_2026_V1',
                'Synthetic service pilot', 'professional_and_implementation_services', 'service',
                %s, 2000, 1000, 'fixed_service_fee', 'service_package', TRUE,
                'scheduled_service', 'not_applicable')""",
                (Jsonb({"archetype_code": "DISCOVERY_ASSESSMENT", "demand_class": "regular",
                        "service_code": "standard"}),))
            cls.conn.execute("""INSERT INTO customers (customer_id, customer_code, customer_name,
                size_segment, industry, country_code, region, customer_since, account_status)
                VALUES ('PILOT-SERVICE-CUST', 'PILOT-SERVICE-CUST', 'Synthetic service buyer',
                'SMB', 'manufacturing', 'DE', 'DE-NW', '2025-01-01', 'Active')""")
            cls.conn.execute("""INSERT INTO customer_credit_profiles (customer_id, credit_limit,
                unbilled_committed_amount, commitments_as_of_at, commitment_evidence_ref,
                risk_rating, credit_status, default_payment_terms_days, last_review_date)
                VALUES ('PILOT-SERVICE-CUST', 1000000, 0, '2026-09-01T09:00:00Z',
                'PILOT-CREDIT-PROOF', 'Low', 'Active', 30, '2026-08-15')""")
            cls.conn.execute("""INSERT INTO compatibility_rules (compatibility_rule_id,
                catalog_version, rule_name, rule_type, scope_type, source_product_id,
                condition_json, severity, message, priority)
                VALUES ('PILOT-SERVICE-COVERAGE', 'CATALOGUE_2026_V1',
                'Synthetic service coverage', 'installation_eligibility', 'line',
                'PILOT-SERVICE', %s, 'blocker', 'Service region eligibility', 1)""",
                (Jsonb({"country_code": "DE", "region": "DE-NW", "eligible": True}),))
            cls.conn.execute("""INSERT INTO deals (deal_id, customer_id, salesperson_id,
                deal_name, submitted_at, catalog_version, policy_set_code,
                requested_delivery_date, destination_country_code, destination_region,
                terms_json, deal_status, dataset_type)
                VALUES ('PILOT-SERVICE-DEAL', 'PILOT-SERVICE-CUST', 'SALES-001',
                'Synthetic service quote', '2026-09-01T10:00:00Z', 'CATALOGUE_2026_V1',
                'BASELINE_2026', '2026-09-10', 'DE', 'DE-NW', %s,
                'Draft', 'generated_test')""",
                (Jsonb({"payment_terms_days": 30, "contract_clause_codes": ["standard"],
                        "allow_partial_delivery": False}),))
            cls.conn.execute("""INSERT INTO deal_lines (deal_line_id, deal_id, line_number,
                product_id, quantity, quoted_unit_price, configuration_json)
                VALUES ('PILOT-SERVICE-LINE', 'PILOT-SERVICE-DEAL', 1,
                'PILOT-SERVICE', 1, 2000, '{}')""")
            cls.conn.execute("UPDATE deals SET deal_status='Submitted' WHERE deal_id='PILOT-SERVICE-DEAL'")
            cls.conn.execute("""INSERT INTO deal_runs (run_id, deal_id, original_policy_set_code,
                applied_policy_set_code, catalog_version_used, as_of_at, data_snapshot_ref,
                input_snapshot_json, config_hash, run_status, started_at)
                VALUES (%s, 'PILOT-SERVICE-DEAL', 'BASELINE_2026', 'BASELINE_2026',
                'CATALOGUE_2026_V1', '2026-09-01T12:00:00Z', 'PILOT-SERVICE-SNAPSHOT',
                '{}', 'pilot-config', 'queued', '2026-09-01T12:00:00Z')""", (RUN_ID,))
        except Exception:
            cls.conn.rollback()
            cls.conn.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        cls.conn.close()

    def setUp(self):
        self.conn.execute("SAVEPOINT service_case")

    def tearDown(self):
        self.conn.execute("ROLLBACK TO SAVEPOINT service_case")
        self.conn.execute("RELEASE SAVEPOINT service_case")

    def decision(self):
        bundle = read_run(self.conn, RUN_ID, commercial_rule_mode="compiled")
        return bundle, assemble_deal_decision(bundle)

    def test_eligible_coverage_only_proposes_an_uncommitted_slot(self):
        bundle, decision = self.decision()
        service = bundle["facts"]["lines"][0]["service"]
        self.assertEqual(service["status"], "conditional")
        self.assertFalse(service["slot_committed"])
        self.assertEqual(decision["status"], "needs_commitment")
        self.assertIn({"line_id": "PILOT-SERVICE-LINE", "code": "service_slot_uncommitted"},
                      decision["uncommitted_paths"])
        self.assertEqual(decision["specialists"]["availability"][0]["source_ids"],
                         ["PILOT-SERVICE-COVERAGE"])
        self.assertIsNone(decision["specialists"]["availability"][0]["earliest_full_date"])

    def test_explicitly_ineligible_region_requires_revision(self):
        self.conn.execute("UPDATE compatibility_rules SET condition_json=%s "
                          "WHERE compatibility_rule_id='PILOT-SERVICE-COVERAGE'",
                          (Jsonb({"country_code": "DE", "region": "DE-NW", "eligible": False}),))
        _, decision = self.decision()
        self.assertEqual(decision["status"], "needs_revision")

    def test_absent_coverage_requires_evidence(self):
        self.conn.execute("DELETE FROM compatibility_rules "
                          "WHERE compatibility_rule_id='PILOT-SERVICE-COVERAGE'")
        _, decision = self.decision()
        self.assertEqual(decision["status"], "needs_evidence")


if __name__ == "__main__":
    unittest.main()
