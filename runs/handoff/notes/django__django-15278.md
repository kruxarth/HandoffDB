## Handoff note

**Issue:** Adding a nullable `OneToOneField` via `migrations.AddField` crashes on SQLite with `OperationalError: Cannot add a UNIQUE column`. The failing SQL is `ALTER TABLE ... ADD COLUMN ... UNIQUE REFERENCES ...`.

**Key code:** `django/db/backends/sqlite3/schema.py:325-333` is the relevant `add_field()` decision point. Line 331 routes unique/primary-key fields to `_remake_table()` (defined at line 145); line 333 falls back to `super().add_field()`. The failing `UNIQUE` column SQL is produced by `django/db/backends/base/schema.py:254-258` (`column_sql()` appends `UNIQUE`) and `django/db/backends/base/schema.py:491+` (`add_field()`).

**Tests:** `tests/schema/tests.py:502-526` (`test_add_field`) currently adds only a nullable `IntegerField` and asserts no table rebuild. It does not cover adding a nullable unique/`OneToOneField`. Add a regression test there or nearby using `OneToOneField(null=True)`. `tests/schema/models.py` contains the schema test models. Migration-operation tests in `tests/migrations/test_operations.py` cover `AddField` generally but not this SQLite schema-editor path.

**Docs:** `docs/releases/4.1.txt` is the current release-notes file; no existing SQLite/`add_field` note was found.

**Ruled out:** The issue is not in migration serialization/autodetection; `AddField` tests and docs were checked. It is not a general `column_sql()` problem, since other backends can add unique columns. The failure is specific to SQLite’s `add_field()` fallback path.

**Conclusion:** Fix belongs in `django/db/backends/sqlite3/schema.py:325-333`: ensure nullable unique `OneToOneField` additions use `_remake_table()` instead of base `ALTER TABLE ADD COLUMN`. Add a focused schema regression test.
