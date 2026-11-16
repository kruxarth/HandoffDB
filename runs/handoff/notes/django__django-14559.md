# Handoff: `bulk_update()` return value

## Issue
`QuerySet.bulk_update()` currently returns `None`; it should return the number of rows matched, like `update()`.

## Relevant code
- `django/db/models/query.py:527-568` — `QuerySet.bulk_update()`.
  - `543-544`: empty `objs` returns early; this should return `0`, not `None`.
  - `550-568`: batching loop calls `update()` per batch; accumulate each batch’s return value and return the total.
- `django/db/migrations/state.py:341` — unrelated `StateApps.bulk_update()` context manager; do not change.

## Tests
- `tests/queries/test_bulk_update.py` — primary test suite. Add/adjust assertions for return values, especially:
  - `test_simple` around lines 27-33.
  - `test_multiple_fields` around lines 36-48.
  - batch-size behavior around lines 51-55.
  - empty input / validation cases around lines 57-61.
- `tests/postgres_tests/test_bulk_update.py` — Postgres-specific bulk update coverage; verify return value if practical.

## Docs
- `docs/ref/models/querysets.txt` — `bulk_update()` reference; document the new integer return value.

## Ruled out
- `StateApps.bulk_update()` in migrations is a different API and unrelated.
- No separate implementation exists elsewhere; `grep` found only `QuerySet.bulk_update()` and the migrations context manager.

## Conclusion
Implement by summing `update()` results inside the batch loop in `QuerySet.bulk_update()` and returning that total. Return `0` for an empty iterable. Update `tests/queries/test_bulk_update.py` to assert counts and update the queryset reference docs.
