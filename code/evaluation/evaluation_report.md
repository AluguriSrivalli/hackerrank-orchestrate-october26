# Evaluation Report

## Scope

The deterministic audit engine was run against all 518 rows in `dataset/deletion_requests.csv`. The labeled benchmark consists of 32 cases in `sample_deletion_requests.csv` with expected results in `sample_output.csv`.

## Current benchmark

| Metric | Result |
|---|---:|
| Case-level status accuracy | **32 / 32 = 100.0%** |
| Exact step-sequence accuracy | **17 / 32 = 53.1%** |
| Semantic step precision / recall / F1 (excluding step_no) | **92.4% / 88.6% / 90.5%** |
| Aligned step-object accuracy | **161 / 185 = 87.0%** |
| Aligned field accuracy | **1,233 / 1,295 = 95.2%** |
| Expected / predicted step counts | **193 / 185** |

Aligned field accuracy compares `step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, and `evidence_id` at corresponding array positions. Semantic step precision/recall/F1 compares unordered full semantic step signatures while excluding only `step_no`; the aligned object metric includes `step_no`. Exact sequence remains the strictest measure and requires the full ordered arrays to match.

## Full output structural validation

- Requests processed: **518**
- Output rows: **518**
- Required header: `case_id,deletion_status,steps_json`
- Status counts: **164 COMPLETE**, **352 INCOMPLETE**, **2 NOT_APPLICABLE**
- Invalid JSON arrays: **0**
- Non-consecutive step numbering: **0**
- Invalid evidence references: **0**
- Findings without evidence: **0**
- `COMPLETE` rows containing non-verification steps: **0**
- `NOT_APPLICABLE` rows containing steps: **0**

Structural validation checks output integrity, not the truth of each deletion claim.

## Source completeness audit

- Evidence manifest entries: **94**
- Evidence files present under `dataset/evidence/`: **94**
- Manifest paths missing on disk: **0**
- Evidence files absent from the manifest: **0**
- Extracted evidence records: **3,564** (logs 1,663; JSON 948; SQL 891; snapshots 38; document/OCR records plus catalog confirmations 24)
- Explicit data-catalog resource-to-user links: **12** across **12** resource IDs

File-level manifest completeness is now checked separately from record-level extraction. A manifest-complete directory does not prove every page, image, or row was successfully interpreted; OCR-derived associations remain lower-confidence than structured records.

## Changes in this iteration

1. **Multi-record document extraction:** PDF/image evidence no longer gets silently skipped just because it mentions multiple resource IDs. Each resource is extracted with a local text neighborhood, and identifiers are attached only when unambiguous in that neighborhood.
2. **Authoritative catalog aliases:** Explicit catalog links participate in resolving request emails to user IDs, including historical addresses not present on the current identity row. Ambiguous email-to-user mappings fail closed as `INCOMPLETE`.
3. **Evidence selection:** When observations agree on interpreted state, source authority helps select the best evidence; state-changing observations are still handled according to timestamp/state semantics. This prevents low-authority retries from replacing better structured evidence in same-state cases.
4. **Object-storage mapping:** `object_*` resources and explicit attachment-catalog confirmations are represented with policy-aware attachment handling.
5. **Activity ledger reuse:** The activity ledger is cached for the run rather than reread for every request.
6. **Structured log parsing:** Timestamp-prefixed JSON events and trace-level context are parsed alongside `key=value` logs.
7. **Identity fields and readback semantics:** `subject_ref`, `subject_reference`, structured `rows=0`, and HTTP 404 fields are recognized.
8. **Pipe-delimited handover parsing:** Known resource-ID shapes are parsed even when the subject is represented by an internal user ID rather than an email.
9. **Cross-time resource joining:** An explicit identity link to a resource can retrieve other observations of that exact `(system_id, resource_id)`, while each observation is independently filtered by `audit_at`.
10. **Conservative activity locator:** A unique operation close to `reported_at` can locate a de-identified analytics resource; the resource's own state evidence is still required. Ambiguous candidate resources are rejected.
11. **Regression coverage:** The suite contains **25 passing tests**, including the cross-time join, time cutoff, ambiguity refusal, and already-redacted support checks.

## Exact-sequence improvement pass

Across the last two iterations, exact step-sequence accuracy improved from **46.9% (15/32)** to **50.0% (16/32)** and then **53.1% (17/32)**. The latest changes target three recurring issues:

- **Cross-time resource join:** when one observation explicitly links a resource to the subject and a separate historical readback omits subject fields, the engine now joins by exact `(system_id, resource_id)`. Each record is still time-filtered independently, so a later state cannot prove the earlier state.
- **Conservative activity locator:** a unique anonymization operation immediately before `reported_at` can locate a de-identified analytics record, but the record's own at-cutoff evidence must still support the anonymized state. A unique account deletion target can be used only to make a proposed follow-up actionable in an already-incomplete case; the activity event is not proof of absence.
- **Regression safety:** added tests for cross-time joining, cutoff enforcement, and refusing ambiguous activity candidates.

The evaluation pipeline now computes semantic step precision/recall/F1 and writes `mismatch_analysis.md` with per-case missing/extra steps and a root-cause category. `sample_rulebook.md` documents all 32 sample cases and the inferred phase, operation, state, evidence, and ordering rules. `custom_evaluation_cases.md` records four additional regression scenarios. The suite contains **25 passing tests**.

Remaining sequence errors mostly concern ambiguous resource ownership in batched activity windows, resource IDs absent from participant-facing evidence, and one sample where the output expects a support attachment that is not linked to the subject in the extracted document evidence. The engine does not invent identity links merely to match sample labels.

## Reverse-engineered rulebook and automated mismatch analysis

- `sample_rulebook.md`: per-case explanation of all 32 ground-truth sample arrays, including status, each step's policy rationale, and ordering.
- `mismatch_analysis.md`: generated on each evaluator run; lists every mismatch, missing/extra steps, whether expected resource IDs occur in evidence/activity sources, and a primary root-cause category.
- `custom_evaluation_cases.md`: four additional participant-created regression scenarios.

## Request-level evidence coverage diagnostics

The latest coverage pass creates three additional artifacts:

- `request_evidence_coverage.csv`: one row per deletion request, with identity-resolution basis, evidence and distinct resources observed at/before `audit_at`, later evidence excluded from the historical assessment, categories, evidence IDs, and source paths.
- `source_completeness.csv`: one row per manifested or discovered evidence file, with file presence, extraction yield, categories, and review flags.
- `evidence_coverage_report.md`: summary counts and interpretation guidance.

Latest coverage findings:

- Requests represented: **518**
- Manifested evidence files: **94**; missing files: **0**; unmanifested files: **0**
- Files yielding no extracted records: **4** (three PDFs/images and one object-storage screenshot; extraction support or OCR should be reviewed)
- Requests with no matched evidence at/before their audit cutoff: **19**
- Of those, requests with later evidence that is excluded from historical proof: **9**
- Request emails resolve to one identity row in the current identity/audit/catalog lookup: **518**. This is unique email resolution, not proof that every resource is authoritatively linked to that user.

The coverage flags are diagnostic, not completion criteria. In particular, the 19 no-cutoff-evidence cases need source/identity review; the nine later-evidence cases must not use later observations as proof of the earlier state. The four zero-yield files need a targeted extraction review before concluding their contents are irrelevant.

Run the coverage diagnostics after generating `output.csv`:

```bash
python3 code/evaluation/evidence_coverage.py
```

## Remaining mismatches and limitations

- **Unlinked anonymized records:** Some analytics records have all direct identifiers removed and no explicit catalog ownership link. The evidence does not establish which request they belong to; assigning them by ordering or resource-number patterns would be speculative.
- **Account resource attribution:** Some point-in-time 404 records have a resource ID but no subject key, while other requests have only a generic snapshot. The engine does not invent a mapping from user to account ID.
- **Retained security audit records:** Several sample expected outputs name audit records that do not occur in the supplied evidence files. The engine cannot cite those records as observed facts.
- **Evidence selection:** The tie-breaker is intentionally applied only when timestamps are equal or missing; timestamp quality and source clock skew remain possible risks. Some expected audit record IDs are not observed in the supplied evidence.
- **Exact output mismatch:** Only 17 of 32 sample step arrays match exactly. Remaining differences are primarily missing/ambiguous resource associations, expected verification records not present in source evidence, and evidence-ID choice. Status accuracy on 32 cases does not establish hidden-test accuracy.

## Run locally

Generate the full output:

```bash
python3 code/main.py
```

Run regression tests:

```bash
python3 -m unittest discover -s code/evaluation -p "test_*.py"
```

Run the sample benchmark and structural validation:

```bash
python3 code/evaluation/main.py
```

## Safety note

Do not treat `COMPLETE` as formal proof unless the relevant system snapshots are complete and identity/resource links are authoritative. In production, missing or ambiguous evidence should trigger human review rather than inferred ownership.
