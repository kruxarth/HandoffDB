## Handoff note

**Issue:** `JSONField` lookups `has_key`, `has_keys`, and `has_any_keys` fail for numeric-string object keys (e.g. `{"1111": "bar"}`) on SQLite, MySQL, and Oracle. PostgreSQL works because it uses the native `?` operator.

**Key code:** `django/db/models/fields/json.py`
- `compile_json_path()` at lines 129–? converts digit-only path components to array indices (`[1111]`) instead of object keys (`."1111"`). This is correct for `KeyTransform` list indexing but wrong for `has_key*` RHS keys.
- `HasKeyLookup` at lines 172–233 builds the lookup SQL. Backend overrides: `as_mysql()` lines 208–211, `as_oracle()` lines 213–219, `as_sqlite()` lines 229–230.
- Lookup classes: `HasKey` lines 235–239, `HasKeys` lines 241–247, `HasAnyKeys` lines 249–?.

**Tests:** `tests/model_fields/test_jsonfield.py`
- Existing `has_key` coverage at lines 509–570: `test_has_key`, `test_has_key_null_value`, `test_has_key_deep`, `test_has_key_list`, `test_has_keys`.
- Lines 534 and 552–558 distinguish numeric list indexing (`value__1__has_key`) from object-key behavior; preserve this distinction.

**Docs:** `docs/ref/models/querysets.txt` documents JSONField `has_key`, `has_keys`, and `has_any_keys` lookups.

**Ruled out:** PostgreSQL backend behavior; general JSONField serialization; non-numeric keys; and numeric `KeyTransform` list indexing, which must remain array-index behavior.

**Conclusion:** Fix `HasKeyLookup` so RHS keys for `has_key`/`has_keys`/`has_any_keys` are compiled as quoted object keys, not array indices, on SQLite/MySQL/Oracle. Add regression tests using a `"1111"` key and update the lookup docs if needed.
