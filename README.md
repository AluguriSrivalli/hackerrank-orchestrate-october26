# Deletion Audit Agent

A deterministic, evidence-driven Python implementation for the HackerRank Orchestrate October 2026 challenge, “Ghost Data Still Exists.”

## Requirements

- Python 3.10 or newer recommended.
- No API keys, external model services, or paid inference are required.
- Core CSV, JSON, SQL, and log processing uses the Python standard library.
- Optional PDF/image extraction may use `pypdf`, Pillow, and Tesseract OCR if installed. The core solution does not require these optional packages.

## Run

Place `code/` at the repository root alongside the supplied `dataset/` directory, then run:

```bash
python3 code/main.py
```

The script reads `dataset/` and writes root-level `output.csv` with exactly:

```text
case_id,deletion_status,steps_json
```

It processes all rows in `dataset/deletion_requests.csv`.

## Validate

Run the unit tests:

```bash
python3 -m unittest discover -s code/evaluation -p "test_*.py"
```

Run the labeled sample comparison and structural checks:

```bash
python3 code/evaluation/main.py
```

The sample benchmark is a 32-case labeled set. The evaluator reports status accuracy, exact ordered-sequence accuracy, semantic step precision/recall/F1, aligned step-object accuracy, and aligned field accuracy. It also regenerates `code/evaluation/mismatch_analysis.md` for per-case error analysis. Its accuracy is useful for regression testing but is not a guarantee of hidden-test accuracy.

## Design

- Resolve current and historical identifiers.
- Parse JSON snapshots, SQLite-compatible SQL captures, structured logs, text records, and supported document evidence.
- Preserve parent metadata while traversing nested evidence structures.
- Use explicit resource-to-identity catalog links to associate resources with users without treating the link itself as proof that a resource exists.
- Respect each request's `audit_at` cutoff. Evidence after the cutoff may help identify a resource requiring follow-up, but is not treated as proof of the earlier state.
- Apply policy-aware handling for deletion, redaction, anonymization, retention, active data flows, and backup restore risks.
- Produce deterministic, ordered findings, remediation actions, and verification steps.

## Limitations

This is a rules-based baseline, not a formal proof of deletion. Some evidence is ambiguous or only partially linked to a subject; a high-stakes deployment should require explicit source completeness guarantees and human review for unresolved identity links. The evaluation report documents the measured sample performance and known failure patterns. `code/evaluation/sample_rulebook.md` reverse-engineers each public sample case before further implementation changes; `custom_evaluation_cases.md` documents additional participant-created regression cases.

## Evidence coverage diagnostics

After generating `output.csv`, run `python3 code/evaluation/evidence_coverage.py` to create `code/evaluation/request_evidence_coverage.csv`, `source_completeness.csv`, and `evidence_coverage_report.md`. These diagnostics separate evidence available at the audit cutoff from later evidence and flag sources that yielded no extracted records. They are review aids, not proof of deletion.
