## Handoff note

**Issue:** `from_db_value()` and other database converters are not applied to values returned by `INSERT ... RETURNING` (`returning_fields`) during `Model.save()`/`create()` or `bulk_create()`. Returned values are assigned raw, so custom fields get plain values instead of wrapper types.

**Relevant code:**
- `django/db/models/sql/compiler.py:1403-1415` — `SQLInsertCompiler.execute_sql()` stores `returning_fields` and returns raw cursor rows; this is where converters must be applied.
- `django/db/models/sql/compiler.py:1100-1123` — `get_converters()`/`apply_converters()` exist and are used by `results_iter()` (~1127-1130), but not by the insert path.
- `django/db/models/base.py:871-875` — `_save_table()` assigns returned values directly via `zip(results[0], returning_fields)`.
- `django/db/models/query.py:1279-1289, 1308` — `_insert()` and `bulk_create()` pass `returning_fields`; returned rows are assigned directly (~506/520).
- `django/db/models/options.py:887` — `db_returning_fields`.
- `django/db/models/fields/__init__.py:747-748` — `get_db_converters()` includes `from_db_value`.

**Tests/models:**
- `tests/queries/test_db_returning.py` — `ReturningValuesTests`; add regression coverage for `create()` and `bulk_create()` with a converting field.
- `tests/queries/models.py` — `CreatedField`, `ReturningModel`, `NonIntegerPKReturningModel` (~725-740).
- `tests/from_db_value/` — existing `from_db_value` behavior for SELECT.
- `tests/custom_pk/fields.py` — `MyAutoField`/`MyWrapper`; `tests/custom_pk/models.py:34` `Bar`; `tests/custom_pk/tests.py:212` `test_custom_field_pk`.
- `tests/bulk_create/` — bulk insert coverage.

**Ruled out:** Converter infrastructure works for normal SELECTs; issue is specific to insert-returning. Not backend-specific: `can_return_columns_from_insert` is true for PostgreSQL/Oracle/MySQL. No `options.py` or field-hook changes needed.

**Docs:** `docs/ref/models/fields.txt` (`from_db_value`) and `docs/ref/models/querysets.txt` (`bulk_create`) describe related behavior; no doc change likely needed.

**Conclusion:** Fix `SQLInsertCompiler.execute_sql()` to apply `get_converters()`/`apply_converters()` to returned `returning_fields` rows before returning them. Add regression tests in `tests/queries/test_db_returning.py`.
