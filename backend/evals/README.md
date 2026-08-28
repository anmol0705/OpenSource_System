# Investigator Eval Harness

Measures REAL Investigator quality against known-correct historical fixes —
distinct from `tests/`, which is fast, free, mocked unit tests run on every
commit. This makes real LLM calls and costs real money; run deliberately,
not automatically.

## Usage

```bash
# from backend/
python -m evals.run_investigator_eval
```

## Adding examples

Each entry in `dataset.json` needs a real, verifiable ground truth — the
actual file changed in a real merged PR that fixed a real issue. Include
`source_pr_url` as an audit trail proving the ground truth is real.

Currently empty — populate before running.
