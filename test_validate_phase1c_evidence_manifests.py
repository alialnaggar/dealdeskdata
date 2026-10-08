import copy
from datetime import date
from pathlib import Path
import unittest

import yaml

from validate_phase1c_evidence_manifests import (
    resolve_references, validate_provider_manifest, validate_snapshot_manifest,
)


HERE = Path(__file__).resolve().parent
CONTRACT = yaml.safe_load((HERE / "phase1c_data_contract.yaml").read_text())
PROVIDER = {
    "schema_version": 1,
    "records": [{
        "evidence_ref": "PROOF-1", "evidence_type": "provider_proof",
        "source_class": "synthetic_provider_manifest", "issued_at": "2026-09-01T09:00:00Z",
        "product_id": "P-1", "provider_id": "SUP-1",
        "configuration_signature_json": {"edition": "business"}, "region_code": "DE",
        "term_code": "12m", "capacity_unit": "instance", "capacity_total": 10,
        "quantity_allocated": 2, "commitment_status": "binding",
        "verified_at": "2026-09-01T09:00:00Z", "covers_from": "2026-09-03",
        "covers_until": "2027-09-04", "confirmed_at": "2026-09-01T09:00:00Z",
        "valid_until": "2027-09-05T00:00:00Z",
    }],
}


class EvidenceManifestTests(unittest.TestCase):
    def test_provider_manifest_and_reference_resolution(self):
        self.assertEqual(validate_provider_manifest(PROVIDER, CONTRACT,
                                                    evaluation_at="2026-09-01T12:00:00Z",
                                                    requested_from=date(2026, 9, 4),
                                                    requested_until=date(2027, 9, 4)), [])
        ref = {"evidence_ref": "PROOF-1", "evidence_type": "provider_proof",
               "source_class": "synthetic_provider_manifest", "issued_at": "2026-09-01T09:00:00Z"}
        self.assertEqual(resolve_references([ref], PROVIDER["records"]), [])

    def test_provider_manifest_rejects_partial_or_future_binding(self):
        bad = copy.deepcopy(PROVIDER)
        bad["records"][0]["quantity_allocated"] = 11
        bad["records"][0]["verified_at"] = "2026-09-11T00:00:00Z"
        errors = validate_provider_manifest(bad, CONTRACT, evaluation_at="2026-09-10T00:00:00Z")
        self.assertTrue(any("within capacity" in e for e in errors))
        self.assertTrue(any("after evaluation" in e for e in errors))

    def test_partial_term_is_not_a_binding_proof(self):
        errors = validate_provider_manifest(PROVIDER, CONTRACT,
            evaluation_at="2026-09-01T12:00:00Z",
            requested_from=date(2026, 9, 4),
            requested_until=date(2027, 10, 4))
        self.assertTrue(any("does not cover requested term" in e for e in errors))

    def test_snapshot_manifest_checks_hashes_and_as_of(self):
        p = HERE / "phase1c_data_contract.yaml"
        import hashlib
        manifest = {"schema_version": 1, "snapshot_id": "SNAP-1",
                    "as_of_at": "2026-09-01T12:00:00Z", "entries": [{
                        "path": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                        "role": "contract"}]}
        self.assertEqual(validate_snapshot_manifest(manifest, base_dir=HERE,
                                                     evaluation_at="2026-09-02T00:00:00Z"), [])
        manifest["entries"][0]["sha256"] = "0" * 64
        self.assertTrue(any("mismatch" in e for e in validate_snapshot_manifest(manifest, base_dir=HERE)))

    def test_missing_independent_record_is_rejected(self):
        self.assertTrue(any("no independent record" in e for e in resolve_references(
            [{"evidence_ref": "MISSING"}], PROVIDER["records"])))

    def test_pilot_snapshot_manifest_matches_all_pinned_inputs(self):
        manifest = __import__("json").loads(
            (HERE / "phase1c_pilot_snapshot_manifest.json").read_text())
        self.assertEqual(validate_snapshot_manifest(manifest, base_dir=HERE,
                                                     evaluation_at="2026-09-02T00:00:00Z"), [])


if __name__ == "__main__":
    unittest.main()
