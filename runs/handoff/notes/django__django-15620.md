# Handoff: SQL comment for deliberately no-op migration operations

## Issue
`sqlmigrate` prints each operation's `-- <description>` header but emits nothing for operations that reduce to no SQL (e.g. `AlterField` where nothing changes), making it unclear whether a no-op occurred. We want an extra comment like `-- (no-op)` after such operations.

## Key files/lines
- `django/db/migrations/migration.py` — `Migration.apply()` lines 92–120 and `unapply()` lines 136–180. These are the only places that append the `--` and `-- %s % operation.describe()` headers to `schema_editor.collected_sql`. The fix belongs here: snapshot `len(schema_editor.collected_sql)` before calling `operation.database_forwards/backwards`, and if unchanged after, append the no-op comment.
- `django/db/backends/base/schema.py` — `__init__` lines 138–142 creates `collected_sql`; `execute()` (~line 160) appends SQL only when `collect_sql` is true.
- `django/db/migrations/loader.py` — `collect_sql()` lines 365–385 aggregates statements.
- `django/core/management/commands/sqlmigrate.py` line 80 invokes it.

## Tests
- `tests/migrations/test_commands.py`: `MigrateTests.test_sqlmigrate_forwards` (line 825), `test_sqlmigrate_backwards` (874), `test_sqlmigrate_for_non_atomic_migration` (930), `test_sqlmigrate_for_non_transactional_databases` (943). These assert on `sqlmigrate` output and should be extended/updated.
- `tests/migrations/test_operations.py`: `test_run_sql_noop` (4120) and `test_run_python_noop` (4663) cover no-op RunSQL/RunPython but not the comment output.

## Docs
`docs/ref/django-admin.txt` (`sqlmigrate`) and `docs/topics/migrations.txt`.

## Ruled out
`Operation.reduces_to_sql` and `RunSQL.noop`/`RunPython.noop` are unrelated (they cover operations that can never be written as SQL, already handled at lines 106–111/170–175). The early return in `BaseDatabaseSchemaEditor.alter_field` (line 694, `_field_should_be_altered`) is the actual no-op source but detection must happen in `migration.py`.

## Conclusion
Implement no-op detection in `Migration.apply`/`unapply` by diffing `collected_sql` length around each operation; update sqlmigrate tests accordingly.
