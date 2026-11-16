# Handoff: table/column comments (db_table_comment / db_comment)

**Issue.** Add DB-level table and column comments: `Meta.db_table_comment` and `Field(db_comment=...)` (ticket proposal). Repo is Django 4.2 alpha; the feature does not exist yet.

**Findings (paths/lines).**
- `django/db/models/options.py`: `DEFAULT_NAMES` 29–59 (`db_table` 32, `db_tablespace` 39); `Options.__init__` 114/128; auto table name 237–241. A `db_table_comment` option must be added to `DEFAULT_NAMES`, initialised, and echoed in `contribute_to_class`'s option loop (197).
- `django/db/models/fields/__init__.py`: `Field.__init__` 179, `db_column` 197/223, `help_text` 198/221, `deconstruct` defaults 539–540 and output 1011/1044. A `db_comment` kwarg needs the same treatment.
- `django/db/backends/base/schema.py`: `sql_create_table` 83, `table_sql` 203–272 (assembles column SQL + constraints), `_iter_column_sql` 286, `column_sql` 341, `create_model` 438, `delete_model` 457, `add_field` 628, `alter_field` 734. Comment clauses belong in `table_sql`/`column_sql`, plus a way to alter a table comment.
- `django/db/migrations/operations/models.py`: `ModelOptionOperation` 471, `AlterModelTable` 481–530 — model for a new `AlterModelTableComment`/`AlterModelOptions` path.
- `django/db/migrations/autodetector.py`: `generate_altered_db_table` 1534–1551 and `AlterModelOptions.ALTER_OPTION_KEYS` 1579–1589.
- Backend feature flag: none in `django/db/backends/base/features.py` (near `supports_table_check_constraints` 189); a `supports_comments` flag is needed for MySQL/Oracle/PostgreSQL vs SQLite.

**Tests.** `tests/schema/tests.py` (`test_db_table` 3347; file 5080 lines), `tests/migrations/test_operations.py` (`test_alter_model_table` 1696), `tests/migrations/test_autodetector.py` (2267–2313), `tests/backends/test_ddl_references.py`, `tests/model_options/models/tablespaces.py`. Docs: `docs/ref/models/options.txt`, `docs/ref/models/fields.txt` (not yet inspected).

**Ruled out.** `grep` for `db_table_comment|db_comment|db_column_comment|supports_comments` across `django/` and `tests/` returns nothing — no partial implementation. "comment" hits in `tests/migrations/test_state.py`/`test_writer.py` are an unrelated model name and file-header comments.

**Conclusion.** Greenfield feature; implementation must span model options, fields, schema editor, backends, migrations/autodetector, plus tests and docs.
