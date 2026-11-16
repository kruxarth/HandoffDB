# Handoff: SQLite table remake crashes on unique constraint

**Issue:** Altering a field (`AlterField` on `value`) on SQLite with a `UniqueConstraint("name", "value")` raises `sqlite3.OperationalError: the "." operator prohibited in index expressions` during the table remake.

**Root cause / key code:**
- `django/db/backends/sqlite3/schema.py:421-437` — `add_constraint`/`remove_constraint` route `UniqueConstraint` containing expressions to `super()` (creating a unique index), and everything else to `_remake_table`. The crash happens inside `_remake_table` while replaying the constraint as an expression index during `AlterField`.
- `django/db/backends/base/schema.py:156-210` (`table_sql`) and `1213-1290` (`_unique_sql`/`_create_unique_sql`) build the unique index SQL.
- `django/db/models/constraints.py:163` (`contains_expressions`) and `:198` (`create_sql`).
- Expression SQL comes from `django/db/models/expressions.py:582` (`F`) and `:845` (`Col.as_sql`, which emits `"table"."column"` — the illegal dotted form in a SQLite index expression). Resolution path: `django/db/models/sql/query.py:1699` (`resolve_ref`).

**Ruled out:** The initial `AddConstraint` succeeds; only the subsequent `AlterField` (remake) fails. Not a docs-only problem, not a model-validation issue, and not in `django/db/models/options.py` name formatting.

**Conclusion:** SQLite's `_remake_table` regenerates the expression unique index with a table-qualified `Col`, which SQLite forbids in index expressions. Fix belongs in the SQLite schema editor (strip the alias/qualifier when generating expression index SQL), possibly also in the base `_create_unique_sql` expression compilation. Confirm scope before editing.

**Tests:** `tests/schema/tests.py` (add a regression test: model with `UniqueConstraint` on two fields, then `AlterField`, asserting no error on SQLite). Also review `tests/schema/models.py`.

No files were edited; no tests run (env lacks `asgiref`; network blocked).
