# Handoff: SQLite drops explicit PK on `AlterField`

## Issue
On SQLite, a migration altering a model's primary key drops the explicit PK: `_remake_table()` demotes every PK field (including the field being altered) before rebuilding, then restores only one.

## Code
- `django/db/backends/sqlite3/schema.py`, `_remake_table()`, lines 215–225: when `create_field` or `alter_field[1]` is a PK, it loops over model fields, sets `field.primary_key = False`, and stores `restore_pk_field`.
- Same file, lines 354–355: restores `restore_pk_field.primary_key = True` after the remake.
- Bug: when the altered field is itself the old PK (`field is alter_field[0]`), it is wrongly demoted. Add a guard for that case.
- Other PK references in the same file: lines 380, 408, 463–465.

## Tests/docs
- `tests/schema/tests.py`: `test_alter_implicit_id_to_explicit` (1554), `test_alter_int_pk_to_autofield_pk` (1611), `..._bigautofield_pk` (1641), `..._smallautofield_pk` (1672), `test_alter_primary_key_quoted_db_table` (921), `test_char_field_pk_to_auto_field` (452). Add the regression test near line 1554.
- `tests/migrations/test_operations.py`: `test_alter_field_pk` (~1784), `test_alter_field_pk_fk` (~1815).
- `docs/releases/4.1.txt`: release notes; no SQLite PK entry yet.

## Ruled out
- Autodetector/state: `django/db/migrations/autodetector.py` 596–648 only tracks `primary_key_rel` for FKs.
- Base editor: `django/db/backends/base/schema.py` 1399–1406 `_field_became_primary_key`; SQLite bypasses this via table remake.
- Introspection: `django/db/backends/sqlite3/introspection.py` 159–394 detects PKs correctly.

## Conclusion
Fix belongs in the `_remake_table()` guard; add a regression test in `tests/schema/tests.py`. The environment lacks `asgiref`/`sqlparse` and network is blocked, so tests and the repro could not be run.
