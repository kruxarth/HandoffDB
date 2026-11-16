# Handoff: DB cache runs `COUNT(*)` twice per `set()`

**Issue.** `DatabaseCache.set()` runs `SELECT COUNT(*)` to check `MAX_ENTRIES`, then `_cull()` runs the same query again right after deleting expired rows — two slow counts per cache write on large tables (Postgres). The second count is derivable from the first minus the rows deleted.

**Code.** `django/core/cache/backends/db.py`
- `set()`, ~lines 118–131: first `SELECT COUNT(*)` into `num`, then `if num > self._max_entries: self._cull(db, cursor, now)`.
- `_cull()`, lines 250–263: `_cull_frequency == 0` branch, expiry `DELETE`, second `SELECT COUNT(*)`, then `cull_num = num // self._cull_frequency` and the `cache_key_culling_sql()` delete.
- `base.py` ~line 69 parses `MAX_ENTRIES`/`CULL_FREQUENCY` into `_max_entries`/`_cull_frequency`.

**Tests/docs.** `tests/cache/tests.py`: cull cache configs at 256–257 (`cull`, `zero_cull`), `_perform_cull_test`/`test_cull`/`test_zero_cull`/`test_cull_delete_when_store_empty` at 632–667, plus `test_zero_cull` for another backend at 1141. There is no `assertNumQueries` anywhere in this file, so nothing pins the query count — add one for the db backend. The docs grep for `MAX_ENTRIES`/`CULL_FREQUENCY` was inconclusive this session; check `docs/topics/cache.txt` before touching option semantics.

**Ruled out.** Periodic culling (new `CULL_EVERY_X` setting): a behavior/API change needing maintainer buy-in, deliberately not implemented. `filebased._cull` (98–112) and `locmem._cull` (97–102) take no arguments and are independent — no cross-backend refactor.

**Conclusion.** Change the signature to `_cull(self, db, cursor, now, count)`; after the expiry `DELETE`, use `deleted_count = cursor.rowcount` and `num = count - deleted_count`. This also holds for the `_cull_frequency == 0` branch (num becomes 0). Keep `num // self._cull_frequency` unchanged. Verify `rowcount` reliability across backends and lock the single-count behavior in with `assertNumQueries`.
