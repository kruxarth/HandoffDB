# Handoff: Migrations marked applied when deferred SQL fails

## Issue
Migrations are recorded as applied even when deferred SQL (foreign keys, indexes, etc.) fails. The earlier fix c86a3d80a25acd1887319198ca21a84c451014ad for #29721 did not account for `SchemaEditor` accumulating `deferred_sql` and executing it only at `__exit__`.

## Key files/lines
- `django/db/migrations/executor.py:82` onward (`MigrationExecutor.migrate`) — records the migration via `self.record_migration()` inside the `with connection.schema_editor(...)` block, i.e. before `__exit__` runs deferred SQL.
- `django/db/backends/base/schema.py:108` — `self.deferred_sql = []` initialized in `__enter__`.
- `django/db/backends/base/schema.py:114-120` — `__exit__` iterates and executes `deferred_sql` only when `exc_type is None`; this is the unguarded failure point.
- `django/db/backends/base/schema.py:155,183,194,333,496,514,1195` — sites appending deferred SQL (FKs, indexes, unique constraints); `352-354,545-547` remove deferred SQL when objects are dropped.

## Tests/docs
- `tests/migrations/test_executor.py` — `test_non_atomic_migration` (106) and `test_atomic_operation_in_non_atomic_migration` (120) cover operation atomicity, not deferred SQL failure. Add a regression test here that mocks a failing deferred statement and asserts `recorder.applied_migrations()` lacks the migration.
- `tests/migrations/test_commands.py`, `tests/schema/tests.py`, `tests/indexes/tests.py` reference deferred SQL behavior.
- Docs: `docs/topics/migrations.txt` (atomicity), `docs/ref/schema-editor.txt`.

## Ruled out
- Could not inspect c86a3d80 directly — the snapshot (`580563a`) has no history (`git show` returned nothing).
- Deferred SQL collection/removal logic is correct; the defect is ordering of the recorder call relative to `SchemaEditor.__exit__`.
- Existing atomic-operation tests do not exercise this path.

## Conclusion
Defer `record_migration()` until after `schema_editor.__exit__` when `schema_editor.deferred_sql` is non-empty (or always record after the `with` block), so a failed deferred statement leaves the migration unapplied. Add the regression test above.
