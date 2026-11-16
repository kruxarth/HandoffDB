# Handoff: SQLite `get_relations()` should use PRAGMA

## Issue
`DatabaseIntrospection.get_relations()` in the SQLite backend parses table DDL with a complex regex to extract foreign keys. SQLite exposes this reliably via `PRAGMA foreign_key_list`, already used by `_get_foreign_key_constraints()`. Refactor `get_relations()` to reuse that path.

## Key files and line ranges
- `django/db/backends/sqlite3/introspection.py`
  - `class DatabaseIntrospection` — line 57
  - `get_relations()` — line 115 (regex/DDL parsing to replace)
  - `_get_foreign_key_constraints()` — lines 183–185, executes `PRAGMA foreign_key_list(%s)` with `quote_name`
  - `get_constraints()` — line 395, calls `_get_foreign_key_constraints`
- `django/db/backends/base/introspection.py`
  - `get_relations()` — lines 147–154 (base contract: returns `{field_name: (other_field, other_table)}`); `get_constraints()` at 166. Adapter needed: PRAGMA/constraints data is structured, not this dict shape.

## Tests
- `tests/introspection/tests.py` — `test_get_relations` (line 134), regression for field removal (line 145), `test_get_relations_alt_format` (line 156). Cross-backend; must still pass.
- `tests/backends/sqlite/test_introspection.py` — SQLite-specific introspection tests; no `get_relations`/PRAGMA coverage currently, so add a test here.
- `tests/backends/base/test_introspection.py` lines 29–32 — base `NotImplementedError` test only.

## Docs
- `docs/releases/4.1.txt` line 251 notes `get_relations()` replaces `get_key_columns()`. No docs describe PRAGMA usage; no doc change likely needed beyond release notes if behavior changes.

## Ruled out
- No SQLite-specific `get_relations` tests exist.
- Base test only asserts `NotImplementedError`, not behavior.
- No `docs/ref/databases.txt` PRAGMA references.

## Conclusion
Replace the regex/DDL logic in `get_relations()` (line 115) with a call to `_get_foreign_key_constraints()` (line 183), mapping its constraint output into the required `{field: (other_field, other_table)}` dict. Verify `tests/introspection/tests.py` and add coverage in `tests/backends/sqlite/test_introspection.py`.
