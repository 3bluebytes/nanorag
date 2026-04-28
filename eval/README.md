# Eval

This directory contains the retrieval evaluation harness inputs and outputs for
rag-nano v1.

## Files

- `cases.yaml` — source of truth for evaluation cases (one entry per case).
- `history.jsonl` — append-only log of evaluation runs. One JSON record per
  `rag-nano eval` invocation. Never edited or rewritten by code.

## Case schema

See `specs/001-minimal-rag-loop/data-model.md` (`EvaluationCase`) for the full
field-by-field definition. Required fields:

| Field                  | Type                         | Notes                                          |
|------------------------|------------------------------|------------------------------------------------|
| `case_id`              | str                          | Stable, human-readable (e.g. `faq-zh-001`).    |
| `query`                | str                          | Query string issued to the retriever.          |
| `query_lang`           | `"zh" \| "en" \| "mixed"`    | Drives the language composition rule.          |
| `expected_data_type`   | `DataType` value             | Data type the case validates against.          |
| `mode`                 | `"chunk_ids" \| "substring"` | Selects which expected field applies.          |
| `expected_chunk_ids`   | list[str]                    | Required when `mode == "chunk_ids"`.           |
| `expected_substring`   | str                          | Required when `mode == "substring"`.           |
| `notes`                | str                          | Optional free-form context.                    |

## Composition rules

The runner validates these at startup and fails fast if violated:

- ≥ 20 cases total
- ≥ 1 case per `expected_data_type` that is present in the corpus
- ≥ 1 case with `query_lang = "zh"` AND ≥ 1 case with `query_lang = "en"`

T058 also requires the seed file to ship with ≥ 10 zh cases and ≥ 10 en cases.

## Running

```bash
uv run rag-nano eval                  # default k=5, append to eval/history.jsonl
uv run rag-nano eval --k 10
uv run rag-nano eval --fail-on-regression   # exit 1 when recall_delta < 0
```

Per FR-021 a single broken case (e.g. an `expected_chunk_id` no longer in the
index) is recorded in `per_case_outcome` with `hit=false` and does not abort the
run.
