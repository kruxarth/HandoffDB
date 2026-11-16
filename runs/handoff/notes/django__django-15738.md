# Handoff: FK→M2M + unique_together removal migration failure

## Issue
Changing `Authors.project_data_set` from `ForeignKey` to `ManyToManyField` while simultaneously deleting `unique_together = (('project_data_set','state','start_date'),)` in one `makemigrations` produces, at `migrate`:
`ValueError: Found wrong number (0) of constraints for app_authors(project_data_set, state, start_date)`
User is DB-independent (fails on fresh DB) and must split into two migrations as a workaround.

## Relevant code
- `django/db/backends/base/schema.py:520-590` — `alter_unique_together`; `_delete_composed_index` raises the error at ~587 when it finds zero matching unique constraints. This is the failure site, not necessarily the bug.
- `django/db/migrations/autodetector.py:1499-1522` — `generate_removed_altered_unique_together` / `generate_altered_unique_together`.
- `django/db/migrations/autodetector.py:1429-1500` — `_get_altered_foo_together_operations`; computes dependencies for `AlterUniqueTogether`.
- `django/db/migrations/autodetector.py:1073-1090` — `_generate_removed_field`; depends on `order_wrt_unset` and `foo_together_change`.
- `django/db/migrations/autodetector.py:1140-1240` — `generate_altered_fields`; m2m↔concrete cannot be altered (treated as remove+add).
- `django/db/migrations/autodetector.py:268-420` — migration chopping/sorting; determines cross-operation order.
- `django/db/migrations/operations/models.py:535-610` — `AlterTogetherOptionOperation` (`database_forwards` 560-572).

## Tests/docs
- `tests/migrations/test_autodetector.py` (operation ordering) — best place for a regression test using `ProjectState`/`ModelState`.
- `tests/migrations/test_operations.py:3080` — analogous "wrong number (0) of indexes" assertion.
- `tests/invalid_models_tests/test_models.py:244-251` — m2m in `unique_together` validation (separate concern; ruled out as the cause).
- Docs: `docs/ref/migration-operations.txt`, `docs/topics/migrations.txt`.

## Ruled out
Model validation (m2m rejected in `unique_together`) is unrelated; error is runtime schema state. No files edited, no tests run.

## Conclusion
Likely an autodetector dependency-ordering bug: `AlterUniqueTogether` (removal) must run before the old column is dropped by `RemoveField`. Fix belongs in autodetector dependencies, not `schema.py`. Unverified — reproduction blocked (no `asgiref`/`sqlparse`, pip/network unavailable; stub attempt at `/tmp/opencode/stubs`). Next: build an autodetector unit test, inspect generated operation order, then patch.
