# Handoff: RenameModel with db_table should be a no-op

## Issue
`RenameModel` on a model with an explicit `db_table` still issues schema changes: on PostgreSQL it drops/recreates FK constraints, on SQLite it rebuilds the table. It should be a database no-op (state rename still happens).

## Where it matters
- `django/db/migrations/operations/models.py` — `RenameModel` class at line 289; `database_forwards()` at line 319 is the fix site. After `alter_db_table()` it loops `old_model._meta.related_objects` calling `schema_editor.alter_field()` (~lines 330-350), then renames M2M fields whose names derive from the model name (~lines 352-365). These run even when `old_model._meta.db_table == new_model._meta.db_table`.
- `django/db/backends/base/schema.py:468-481` — `alter_db_table()` already returns early when old/new names are equal (or equal ignoring case). So the table rename itself is guarded; the FK/M2M work is not.

## Fix
In `RenameModel.database_forwards()`, return early when the old and new models share the same `db_table` — before `alter_db_table`, the related-object `alter_field` loop, and the M2M rename loop. `state_forwards()` (line 316) must keep renaming the model in state.

## Tests
- `tests/migrations/test_operations.py`: `test_rename_model` (line 600), `test_rename_model_with_m2m` (767), `test_alter_model_table_noop` (1279), and db_table cases at 1304-1316 and 3601-3628 are the models to follow. Add a regression test asserting no SQL/schema change when `db_table` is set (e.g. `assertNumQueries`-free pattern: run forwards, check table and FK unchanged).

## Docs
`docs/ref/migration-operations.txt` (`RenameModel` section).

## Ruled out
`alter_db_table`'s own guard (schema.py:470-473) already covers identical/case-insensitive names, so the table-rename path was not the cause; the residual FK/M2M work in `database_forwards` was.
