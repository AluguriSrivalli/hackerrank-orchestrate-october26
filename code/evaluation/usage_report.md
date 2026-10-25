# Token Usage and Cost Report

## Final full-dataset run

- Requests processed in the final run: **518**
- Evidence records parsed: **3,564**
- Model provider/name: **None — deterministic Python rules**
- Model API calls: **0**
- Input tokens: **0**
- Output tokens: **0**
- Total model tokens: **0**
- Average model tokens per request: **0**
- Estimated total inference cost: **$0.00**
- Estimated cost per request: **$0.00**
- Per-model totals: **Not applicable; no model was called**
- Overall totals: **0 model calls, 0 tokens, $0.00 estimated model cost**

These figures exclude local CPU runtime and any optional third-party OCR dependencies. No API keys or paid inference services are required.

## Reproduce

From the repository root:

```bash
python3 code/main.py
python3 code/evaluation/main.py
python3 -m unittest discover -s code/evaluation -p "test_*.py"
```

Python 3.10+ is recommended. Core CSV, JSON, SQL, and log processing uses the standard library. Optional PDF/image extraction depends on `pypdf`, Pillow, and Tesseract being installed.
