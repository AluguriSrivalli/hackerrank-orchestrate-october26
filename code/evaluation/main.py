#!/usr/bin/env python3
"""Reproduce structural validation and labeled sample metrics.

Run from repository root:
    python3 code/evaluation/main.py
"""
from __future__ import annotations
import csv
import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code" / "main.py"
DATA = ROOT / "dataset"

def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))

def main():
    spec = importlib.util.spec_from_file_location("deletion_audit", CODE)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)

    identities, audits, by_user, email_users = audit.identity_index()
    evidence = audit.load_evidence()
    expected_rows = {r["case_id"]: r for r in read_csv(DATA / "sample_output.csv")}
    sample_requests = read_csv(DATA / "sample_deletion_requests.csv")

    predicted = {}
    for req in sample_requests:
        status, steps = audit.audit_case(req, evidence, by_user, email_users, identities, audits)
        predicted[req["case_id"]] = {
            "deletion_status": status,
            "steps_json": json.dumps(steps, ensure_ascii=False, separators=(",", ":")),
        }

    keys = ("step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id")
    status_correct = exact_sequence = aligned_object = field_correct = field_total = 0
    expected_step_count = predicted_step_count = 0
    semantic_tp = semantic_fp = semantic_fn = 0
    mismatch_rows = []
    for case_id, expected in expected_rows.items():
        actual = predicted.get(case_id)
        if not actual:
            continue
        status_correct += expected["deletion_status"] == actual["deletion_status"]
        exp_steps = json.loads(expected["steps_json"])
        got_steps = json.loads(actual["steps_json"])
        expected_step_count += len(exp_steps)
        predicted_step_count += len(got_steps)
        exact_sequence += exp_steps == got_steps
        # Semantic step metrics exclude step_no so that one insertion does not
        # make every later, otherwise-correct step look like a different action.
        semantic_keys = ("phase", "system_id", "resource_id", "operation", "state", "evidence_id")
        exp_counter = Counter(tuple(step.get(key) for key in semantic_keys) for step in exp_steps)
        got_counter = Counter(tuple(step.get(key) for key in semantic_keys) for step in got_steps)
        common_counter = exp_counter & got_counter
        semantic_tp += sum(common_counter.values())
        semantic_fn += sum(exp_counter.values()) - sum(common_counter.values())
        semantic_fp += sum(got_counter.values()) - sum(common_counter.values())
        if exp_steps != got_steps or expected["deletion_status"] != actual["deletion_status"]:
            mismatch_rows.append((case_id, expected, actual, exp_steps, got_steps))
        for index in range(min(len(exp_steps), len(got_steps))):
            e, g = exp_steps[index], got_steps[index]
            aligned_object += all(e.get(key) == g.get(key) for key in keys)
            for key in keys:
                field_total += 1
                field_correct += e.get(key) == g.get(key)

    output_path = ROOT / "output.csv"
    output = read_csv(output_path)
    requests = read_csv(DATA / "deletion_requests.csv")
    valid_ids = {r["file_id"] for r in read_csv(DATA / "evidence_files.csv")}
    valid_ids |= {r["activity_id"] for r in read_csv(DATA / "system_activity.csv")}
    valid_ids |= {r["audit_id"] for r in read_csv(DATA / "user_audit_log.csv")}
    invalid_json = bad_steps = invalid_evidence = findings_without_evidence = 0
    complete_with_findings = not_applicable_with_steps = 0
    for row in output:
        try:
            steps = json.loads(row["steps_json"])
            if not isinstance(steps, list):
                invalid_json += 1
                continue
        except Exception:
            invalid_json += 1
            continue
        if [s.get("step_no") for s in steps] != list(range(1, len(steps) + 1)):
            bad_steps += 1
        if row["deletion_status"] == "COMPLETE" and any(s.get("phase") != "VERIFICATION" for s in steps):
            complete_with_findings += 1
        if row["deletion_status"] == "NOT_APPLICABLE" and steps:
            not_applicable_with_steps += 1
        for step in steps:
            if step.get("evidence_id") and step["evidence_id"] not in valid_ids:
                invalid_evidence += 1
            if step.get("phase") == "FINDING" and not step.get("evidence_id"):
                findings_without_evidence += 1

    print("SAMPLE BENCHMARK")
    print(f"Status accuracy: {status_correct}/{len(expected_rows)} ({status_correct / max(1, len(expected_rows)):.1%})")
    print(f"Exact step-sequence accuracy: {exact_sequence}/{len(expected_rows)} ({exact_sequence / max(1, len(expected_rows)):.1%})")
    step_precision = semantic_tp / max(1, semantic_tp + semantic_fp)
    step_recall = semantic_tp / max(1, semantic_tp + semantic_fn)
    step_f1 = 2 * step_precision * step_recall / max(1e-12, step_precision + step_recall)
    print(f"Semantic step precision / recall / F1 (excluding step_no): {step_precision:.1%} / {step_recall:.1%} / {step_f1:.1%} ({semantic_tp} TP, {semantic_fp} FP, {semantic_fn} FN)")
    aligned_positions = field_total // len(keys)
    print(f"Aligned step-object accuracy: {aligned_object}/{aligned_positions} ({aligned_object / max(1, aligned_positions):.1%})")
    print(f"Aligned field accuracy: {field_correct}/{field_total} ({field_correct / max(1, field_total):.1%})")
    print(f"Expected/predicted step counts: {expected_step_count}/{predicted_step_count}")
    print()
    print("FULL OUTPUT STRUCTURAL VALIDATION")
    print(f"Requests/output rows: {len(requests)}/{len(output)}")
    print(f"Header valid: {list(output[0]) == ['case_id', 'deletion_status', 'steps_json'] if output else False}")
    print(f"Invalid JSON arrays: {invalid_json}")
    print(f"Invalid step numbering: {bad_steps}")
    print(f"Invalid evidence references: {invalid_evidence}")
    print(f"Findings without evidence: {findings_without_evidence}")
    print(f"COMPLETE rows with non-verification steps: {complete_with_findings}")
    print(f"NOT_APPLICABLE rows with steps: {not_applicable_with_steps}")

    # Produce a reproducible per-case mismatch analysis with evidence-coverage
    # diagnostics. This uses sample_output only for evaluation, never prediction.
    evidence_resource_ids = {str(record.get("resource_id", "")) for record in evidence}
    activity_resource_ids = {
        str(row.get("resource_id", "")) for row in read_csv(DATA / "system_activity.csv")
        if row.get("resource_id")
    }
    participant_resource_ids = evidence_resource_ids | activity_resource_ids
    report_lines = [
        "# Automated Sample Mismatch Analysis", "",
        "Generated by `code/evaluation/main.py`; the sample output is used only as the validation oracle.", "",
        f"- Status accuracy: {status_correct}/{len(expected_rows)} ({status_correct / max(1, len(expected_rows)):.1%})",
        f"- Exact sequence accuracy: {exact_sequence}/{len(expected_rows)} ({exact_sequence / max(1, len(expected_rows)):.1%})",
        f"- Semantic step precision/recall/F1: {step_precision:.1%}/{step_recall:.1%}/{step_f1:.1%}",
        f"- Aligned step-object accuracy: {aligned_object}/{aligned_positions} ({aligned_object / max(1, aligned_positions):.1%})",
        f"- Aligned field accuracy: {field_correct}/{field_total} ({field_correct / max(1, field_total):.1%})", "",
        "## Mismatches", ""
    ]
    if not mismatch_rows:
        report_lines.append("No mismatches.")
    for case_id, expected, actual, exp_steps, got_steps in mismatch_rows:
        report_lines += [f"### {case_id}", "",
            f"- Status expected/predicted: `{expected['deletion_status']}` / `{actual['deletion_status']}`",
            f"- Step count expected/predicted: {len(exp_steps)} / {len(got_steps)}"]
        semantic_keys = ("phase", "system_id", "resource_id", "operation", "state", "evidence_id")
        ec = Counter(tuple(step.get(key) for key in semantic_keys) for step in exp_steps)
        gc = Counter(tuple(step.get(key) for key in semantic_keys) for step in got_steps)
        missing = list((ec - gc).elements())
        extra = list((gc - ec).elements())
        if expected["deletion_status"] != actual["deletion_status"]:
            category = "request classification / identity resolution"
        elif not missing and not extra:
            category = "JSON serialization / step ordering / step numbering"
        elif any(item[2] not in participant_resource_ids for item in missing):
            category = "evidence matching / historical resource recovery (expected resource ID absent from participant-facing sources)"
        elif any(item[2] not in evidence_resource_ids for item in missing):
            category = "identity resolution / evidence matching (resource appears in activity only, without state evidence)"
        elif any(item[2] in evidence_resource_ids for item in missing):
            category = "identity resolution / evidence matching / verification generation"
        else:
            category = "operation/state selection / policy application / extra-step suppression"
        report_lines.append(f"- Primary root-cause category: **{category}**")
        if missing:
            report_lines.append("- Missing expected steps:")
            for item in missing:
                phase, system, resource, operation, state, evidence_id = item
                if resource in evidence_resource_ids:
                    availability = "resource ID present in extracted evidence"
                elif resource in activity_resource_ids:
                    availability = "resource ID present in activity ledger only; no extracted state evidence"
                else:
                    availability = "resource ID not found in participant-facing sources"
                report_lines.append(f"  - `{phase}` `{system}` `{resource}` `{operation}` `{state}` evidence=`{evidence_id or '(blank)'}` — {availability}")
        if extra:
            report_lines.append("- Extra predicted steps:")
            for item in extra:
                phase, system, resource, operation, state, evidence_id = item
                report_lines.append(f"  - `{phase}` `{system}` `{resource}` `{operation}` `{state}` evidence=`{evidence_id or '(blank)'}`")
        if not missing and not extra:
            report_lines.append("- The semantic step set matches; the mismatch is serialization/order/step-numbering only.")
        report_lines.append("")
    report_path = ROOT / "code" / "evaluation" / "mismatch_analysis.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
