# Handoff: `_unregister_lookup()` should clear the lookup cache

**Issue.** `RegisterLookupMixin._unregister_lookup()` deletes from `cls.class_lookups` but never clears the cached lookups, unlike `register_lookup()`. Stale lookups survive unregistration.

**Relevant code (`django/db/models/query_utils.py`):**
- `_clear_cached_lookups()` (~L194–196): iterates `subclasses(cls)` and calls `get_lookups.cache_clear()`.
- `register_lookup()` (~L198–205): sets `class_lookups[lookup_name]` then calls `cls._clear_cached_lookups()` (the L202 referenced in the issue).
- `_unregister_lookup()` (~L207–215): only `del cls.class_lookups[lookup_name]`; **missing** `cls._clear_cached_lookups()` (the L212 gap).

**Consumer / test plumbing:** `django/test/utils.py` L990–1001 defines the `register_lookup` context manager; its `finally` calls `field._unregister_lookup(...)`. This is why the bug leaks into tests.

**Test to update:** `tests/schema/tests.py` L2760 `test_func_unique_constraint_lookups` (inside `SchemaTests`). It wraps `Lower`/`Abs` registration around building/adding a `UniqueConstraint`. With the cache now cleared on exit, SQL/constraint resolution must occur while lookups are still registered (or be re-registered); apply the minor adjustment from PR #15569.

**Docs:** `docs/howto/custom-lookups.txt` and `docs/ref/models/fields.txt` describe `register_lookup`/lookup registration; no behavior change beyond cache invalidation, so likely no doc edit.

**Ruled out:** `register_lookup()` and `_clear_cached_lookups()` are correct; `merge_dicts`/transform resolution irrelevant; `django/test/utils.py` needs no change — it correctly calls `_unregister_lookup`.

**Conclusion.** Add `cls._clear_cached_lookups()` at the end of `_unregister_lookup()` in `django/db/models/query_utils.py` (after the `del`), then adjust `test_func_unique_constraint_lookups` in `tests/schema/tests.py` and run `tests/schema` plus `tests/lookup`.
