## Handoff: SQLite `AlterField` choices should be no-op

**Issue:** On SQLite, changing/adding `choices` on a field triggers a full table remake (create/copy/drop/rename), although `choices` is non-DB metadata. PostgreSQL already emits no SQL.

**Key files/lines:**
- `django/db/backends/sqlite3/schema.py:123-124` — `alter_field()` early guard calls `_field_should_be_altered()`; if it returns `True`, SQLite proceeds to remake.
- `django/db/backends/sqlite3/schema.py:420` — `_alter_field()` unconditionally remakes the table for any alteration reaching it.
- `django/db/backends/base/schema.py:700-756` — base `alter_field()` also uses `_field_should_be_altered()`.
- `django/db/backends/base/schema.py:758+` — base `_alter_field()` compares DB parameters and is where PostgreSQL effectively no-ops.
- `django/db/backends/base/schema.py:1372+` — `_field_should_be_altered()`; it compares `deconstruct()` output, so `choices` is treated as an alteration. The nearby `limit_choices_to` handling at ~1385 shows the existing non-DB-attribute pattern.

**Tests/docs:**
- `tests/schema/tests.py:3920-3970` — existing no-op tests (`test_alter_field_default_doesnt_perform_queries`, `test_alter_field_fk_attributes_noop`). Add a regression test here asserting `assertNumQueries(0)` when only `choices` changes.
- No docs change needed; this is internal schema-editor behavior.

**Ruled out:** Migration serialization/writer (`tests/migrations/test_writer.py`) and `db_parameters`; `choices` does not affect `db_parameters`, and PostgreSQL’s no-SQL behavior confirms the issue is SQLite’s remake path, not migration generation.

**Conclusion:** Make SQLite’s `alter_field()` ignore `choices` when deciding whether to alter, e.g. extend `_field_should_be_altered()` to accept `ignore={"choices"}` and call it from `sqlite3/schema.py:124`. Add the zero-query regression test in `tests/schema/tests.py`.
