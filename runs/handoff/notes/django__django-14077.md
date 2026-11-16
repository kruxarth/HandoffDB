# Handoff: SQLite JSONField `values()` boolean coercion

Issue: `QuerySet.values()/values_list('data__value')` on SQLite returns `1/0` for JSON `true/false`, while PostgreSQL returns booleans.

Relevant code:
- `django/db/models/fields/json.py`, `KeyTransform.as_sql()` around lines 312–320: compiles key transforms to `JSON_EXTRACT(...)`. SQLite returns JSON booleans from `JSON_EXTRACT` as integers.
- `django/db/backends/sqlite3/operations.py`, `get_db_converters()` around line 281 and `convert_booleanfield_value()` around line 325: only BooleanField conversion exists; no JSONField datatype converter is registered. A SQLite JSON datatype mapping/converter using `JSON_TYPE` is needed to map JSON `true`/`false`/`null` to `bool`/`None`.

Tests:
- `tests/model_fields/test_jsonfield.py`, especially `test_key_values` around lines 791–806, which already asserts `value__h` is `True` and `value__i` is `False` via `values_list(flat=True)`. Add/adjust a regression for `values_list('data', 'data__value')` on SQLite.
- Related docs: `docs/ref/models/fields.txt` JSONField and `docs/ref/databases.txt` SQLite notes.

Ruled out: `convert_booleanfield_value` and BooleanField converter registration are unrelated; `JSONExact.process_lhs()` and lookup filtering are not the cause; PostgreSQL behavior is already correct. The fix belongs in SQLite JSON key-transform output conversion, not model serialization.

Conclusion: SQLite must convert JSON boolean/null results from key transforms used by `values()`/`values_list()` using `JSON_TYPE`-aware datatype handling in the SQLite backend.
