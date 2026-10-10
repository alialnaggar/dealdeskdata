"""Validate independent evidence and replay snapshot manifests.

Manifest records are evidence objects. A reference string in a deal row is
accepted only when its complete typed record is present in an independent
manifest and the record is valid at the run's as-of time.
"""

from datetime import datetime
import hashlib
import re


SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _instant(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label}: expected ISO datetime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label}: invalid ISO datetime") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label}: timezone required")
    return parsed


def validate_provider_manifest(manifest, contract, *, evaluation_at=None,
                               requested_from=None, requested_until=None):
    errors = []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return ["provider manifest schema_version must be 1"]
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        return ["provider manifest records must be a nonempty array"]
    spec = contract["json_contracts"]["provider_evidence_record"]
    required = set(spec["required_keys"])
    allowed = required | {"confirmed_at", "valid_until"}
    seen = set()
    cutoff = _instant(evaluation_at, "evaluation_at") if evaluation_at else None
    requested_start = requested_from
    requested_end = requested_until
    for index, record in enumerate(records):
        label = f"records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{label}: must be an object")
            continue
        missing = required - set(record)
        unknown = set(record) - allowed
        errors.extend(f"{label}: missing {key}" for key in sorted(missing))
        errors.extend(f"{label}: unknown key {key}" for key in sorted(unknown))
        ref = record.get("evidence_ref")
        if not isinstance(ref, str) or not ref.strip():
            errors.append(f"{label}: evidence_ref must be nonblank")
        elif ref in seen:
            errors.append(f"{label}: duplicate evidence_ref {ref}")
        seen.add(ref)
        status = record.get("commitment_status")
        if status not in spec["commitment_status"]:
            errors.append(f"{label}: invalid commitment_status")
        total, allocated = record.get("capacity_total"), record.get("quantity_allocated")
        if not isinstance(total, (int, float)) or total < 0:
            errors.append(f"{label}: capacity_total must be nonnegative")
        if not isinstance(allocated, (int, float)) or allocated < 0 or (isinstance(total, (int, float)) and allocated > total):
            errors.append(f"{label}: quantity_allocated must be within capacity_total")
        try:
            verified = _instant(record.get("verified_at"), f"{label}.verified_at")
            start = datetime.fromisoformat(str(record.get("covers_from"))).date()
            end = datetime.fromisoformat(str(record.get("covers_until"))).date()
            if start >= end:
                errors.append(f"{label}: covers_until must be after covers_from")
            issued = _instant(record.get("issued_at"), f"{label}.issued_at")
            if issued > verified:
                errors.append(f"{label}: issued_at is after verified_at")
            if cutoff and verified > cutoff:
                errors.append(f"{label}: verified_at is after evaluation_at")
            if cutoff and issued > cutoff:
                errors.append(f"{label}: issued_at is after evaluation_at")
            if status == "binding" and requested_start and requested_end and (
                    start > requested_start or end < requested_end):
                errors.append(f"{label}: binding record does not cover requested term")
            if status == "binding":
                confirmed = _instant(record.get("confirmed_at"), f"{label}.confirmed_at")
                valid_until = _instant(record.get("valid_until"), f"{label}.valid_until")
                if confirmed > issued or valid_until.date() <= end:
                    errors.append(f"{label}: binding confirmation or expiry is inconsistent")
        except (TypeError, ValueError):
            errors.append(f"{label}: invalid coverage dates")
        if status == "binding" and any(record.get(key) in (None, "") for key in ("confirmed_at", "valid_until")):
            errors.append(f"{label}: binding record needs confirmed_at and valid_until")
    return errors


def validate_snapshot_manifest(manifest, *, base_dir=None, evaluation_at=None):
    errors = []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return ["snapshot manifest schema_version must be 1"]
    snapshot_id = manifest.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        errors.append("snapshot_id must be nonblank")
    try:
        as_of = _instant(manifest.get("as_of_at"), "as_of_at")
        if evaluation_at and as_of > _instant(evaluation_at, "evaluation_at"):
            errors.append("as_of_at is after evaluation_at")
    except ValueError as exc:
        errors.append(str(exc))
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        return errors + ["entries must be a nonempty array"]
    seen = set()
    for index, entry in enumerate(entries):
        label = f"entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: must be an object")
            continue
        for key in ("path", "sha256", "role"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                errors.append(f"{label}: {key} must be nonblank")
        path = entry.get("path")
        digest = entry.get("sha256")
        if path in seen:
            errors.append(f"{label}: duplicate path")
        seen.add(path)
        if isinstance(digest, str) and not SHA256.fullmatch(digest):
            errors.append(f"{label}: sha256 must be lowercase hex")
        if base_dir and isinstance(path, str) and isinstance(digest, str) and SHA256.fullmatch(digest):
            file_path = base_dir / path
            if not file_path.is_file():
                errors.append(f"{label}: file is missing")
            elif hashlib.sha256(file_path.read_bytes()).hexdigest() != digest:
                errors.append(f"{label}: sha256 mismatch")
    return errors


def resolve_references(references, manifest_records):
    """Return errors for refs whose complete independent record is absent."""
    by_ref = {row.get("evidence_ref"): row for row in manifest_records or [] if isinstance(row, dict)}
    errors = []
    for index, reference in enumerate(references or []):
        if not isinstance(reference, dict):
            errors.append(f"references[{index}]: must be an object")
            continue
        ref = reference.get("evidence_ref")
        record = by_ref.get(ref)
        if record is None:
            errors.append(f"references[{index}]: no independent record for {ref}")
            continue
        for key in ("evidence_ref", "evidence_type", "source_class", "issued_at"):
            if reference.get(key) != record.get(key):
                errors.append(f"references[{index}]: {key} differs from manifest")
    return errors
