## Handoff note: DatabaseCache unquoted fields

**Issue:** `DatabaseCache` emits SQL with unquoted column names. Snowflake folds unquoted identifiers to uppercase, so `cache_key`/`expires` fail unless every field is quoted. Reported patch targeted stable/3.2.x; this tree is 4.1 alpha.

**Relevant code:**
- `django/core/cache/backends/db.py`: most fields already use `quote_name()` (e.g. lines 67–71, 138–180, 213). Remaining gaps:
  - lines 231–234: `SELECT ... WHERE cache_key = %s and expires > %s` leaves `expires` unquoted.
  - line 246: `DELETE FROM ... WHERE expires < %s` leaves `expires` unquoted.
  - line 253: culling query comes from `connection.ops.cache_key_culling_sql()`.
- `django/db/backends/base/operations.py:83-92`: base `cache_key_culling_sql()` selects/orders by unquoted `cache_key`.
- `django/db/backends/oracle/operations.py:74-75`: Oracle override has the same unquoted `cache_key`.

**Tests/docs:** `tests/cache/tests.py` — `DBCacheTests` (~1070–1200) already uses `LOCATION='test cache table'` to exercise table-name quoting; cull coverage at ~630–650. Relevant docs: `docs/topics/cache.txt` (database cache section).

**Ruled out:** Table-name quoting is already handled via `connection.ops.quote_name(self._table)` and is covered by the spaced `LOCATION` test. The ORM/model metadata (`Options`) and router are not involved. This is not a wholesale missing-quoting problem; only specific SQL fragments and the culling helper remain.

**Conclusion:** Fix by quoting `expires` in `db.py:231-234` and `db.py:246`, and quoting `cache_key` in both `cache_key_culling_sql()` implementations (base and Oracle). Add a regression test asserting quoted SQL or using a backend that requires identifier quoting.
