# Handoff: rename + db_column should be SQL noop

## Issue
Renaming `core` → `core_renamed` while setting `db_column='core'` produces `RenameField` + `AlterField`, emitting two cancelling `ALTER TABLE ... RENAME COLUMN` statements instead of no SQL (cf. #31826, which fixed the no-rename case).

## Key code
- `django/db/migrations/autodetector.py`
  - `generate_renamed_fields()` (line 817); the rename detection comparing the new field's `db_column` against the old field's implicit column is at lines 836–841. This correctly emits `RenameField`.
  - `generate_altered_fields()` (line 921) then also emits `AlterField` for the added `db_column`; the rename lookup is at line 929. The unwanted pair originates here.
- `django/db/migrations/operations/fields.py`
  - `AlterField` (line 184), `RenameField` (line 254). `RenameField.database_forwards()` calls `schema_editor.alter_field()` with the renamed field, so it renames the column.
- `django/db/backends/base/schema.py`
  - `alter_field` (578), `_alter_field` (621), column-rename branch (713–719).
  - `_field_should_be_altered` (1122) lists `db_column` in `non_database_attrs` (1131–1146); this is the #31826 fix and already makes a standalone `AlterField` a noop.
- `django/db/migrations/state.py`: `rename_field` (259).

## Tests
- `tests/migrations/test_autodetector.py`: `test_rename_field_preserved_db_column` (985), `test_rename_related_field_preserved_db_column` (1013) — these assert `RenameField` is generated but don't assert SQL noop.
- `tests/migrations/test_operations.py`: `test_alter_field_add_db_column_noop` (1359, the #31826 regression), `test_rename_field_with_db_column` (1785).
- `tests/migrations/test_optimizer.py`: `test_alter_field_rename_field` (560).
- Docs: no docs file was inspected; if behavior changes, note it in `docs/releases/4.1.txt`.

## Ruled out
- Schema editor's standalone `db_column` noop: already correct via `_field_should_be_altered`.
- `RenameField` itself: it faithfully renames the column; the problem is that the follow-up `AlterField` undoes it.

## Conclusion (unverified)
Fix likely requires ordering/reduction so the `db_column` `AlterField` is applied *before* the `RenameField` (or merged), making both no-ops — in `operations/fields.py` (`AlterField.reduce`) and/or `autodetector.py`. Focused tests were not run: `asgiref` is missing in the environment (`pip install asgiref` first).
