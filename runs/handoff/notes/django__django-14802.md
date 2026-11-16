## Handoff: `make_and_validate_key` cache helper

**Issue:** Add a `BaseCache.make_and_validate_key(key, version=None)` helper that calls `make_key()` then `validate_key()` and returns the key, replacing repeated pairs across cache backends.

**Code to change**
- `django/core/cache/backends/base.py`: `make_key()` at line 95 and `validate_key()` at line 243. Add the helper near these.
- `django/core/cache/backends/filebased.py`: lines 130–131 are the canonical pair to replace.
- `django/core/cache/backends/memcached.py`: pairs at 70–71, 75–76, 80–81, 87–88, 92–93, 108–109, 129, 170, 184, 203; bulk variants at 97–99 and 137 need care (mapping/list comprehensions).
- `django/core/cache/backends/db.py`: pairs at 98–99, 103–104, 108–109, 230–231. Note lines 59–60, 199–200, and 205–206 call `validate_key()` *before* `make_key()`; these validate the raw key and should be reviewed separately, not blindly converted.
- `dummy.py` and `locmem.py` have no `make_key`/`validate_key` calls; they inherit `BaseCache` and need no changes.

**Tests:** `tests/cache/tests.py` — `BaseCacheTests` starts line 283; key-related tests around lines 685 (`custom make_key`), 714–719 (invalid characters/length), 991 (`test_custom_key_func`), and `CustomCacheKeyValidationTests` at line 1719. Add a direct unit test for the helper, likely in `BaseCacheTests` or `CustomCacheKeyValidationTests`.

**Docs:** `docs/topics/cache.txt` documents `make_key`/custom key functions; add the helper there. `docs/releases/4.0.txt` for a release note.

**Ruled out:** Adding a `validate` flag to `make_key()` — backward-incompatible default and overridden `make_key()` methods would require deprecation/docs. Also out of scope: fixing the existing validate-before-make ordering in `db.py`.

**Conclusion:** Implement the additive helper on `BaseCache`, refactor clear make-then-validate call sites, and leave ambiguous ordering cases unchanged.
