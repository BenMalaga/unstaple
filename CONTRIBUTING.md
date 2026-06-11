# Contributing to unstaple

Thanks for considering it. This project lives or dies by how well its heuristics survive contact with real scanners, so the contribution guide is short and unusual.

## The best contribution: a problem PDF

Heuristics tuned only on synthetic fixtures are a lab experiment. If `unstaple` mis-splits one of your scans, that PDF is worth more than any code patch.

1. **Anonymize it first.** Redact names, addresses, account numbers, anything personal. Rebuilding a lookalike with fake text is even better (see `tests/fixtures/make_fixtures.py` for how the existing fixtures are generated; a generator script is the ideal form for a new fixture).
2. Put real, anonymized PDFs in `tests/fixtures/real/` (tracked by git; the synthetic ones in `tests/fixtures/` are generated and ignored).
3. Open a PR or issue stating: how many documents are actually in the file, where the correct boundaries are, and what `unstaple --dry-run` currently proposes.

A failing test that encodes the correct boundaries is perfect. Do not worry about also fixing the heuristic; a well-described failure is a complete contribution.

## Code contributions

- Keep the core promise: deterministic, explainable, offline. No network calls, no ML models, no nondeterminism in boundary decisions.
- Boundary logic lives in pure functions (`features.py`, `scoring.py`, `naming.py`). New signals should follow that pattern: extract a feature from page text, score it, give it a human-readable reason string.
- Every new signal or weight change must come with tests showing what it fixes and what it does not break. Run `pytest` before sending a PR; CI runs the same suite.
- Runtime dependencies are limited to `pypdf` on purpose. Dev-only dependencies (like reportlab) are fine in the `dev` extra.

## Setup

```console
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Style

- Python 3.10+ syntax, standard library first.
- Reason strings shown to users should be short, lowercase fragments, e.g. `page numbering reset: "Page 1 of 3" after "Page 2 of 2"`.
- No em dashes in docs or help text; plain punctuation only.
