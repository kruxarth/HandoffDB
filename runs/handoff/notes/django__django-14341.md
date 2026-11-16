# Handoff: Database cache `delete` uses cursor after close

## Issue
In `django/core/cache/backends/db.py`, `_base_delete_many()` returns `bool(cursor.rowcount)` at line 228, *outside* the `with connection.cursor() as cursor:` block (line 219). Per PEP 249, the cursor is unusable after `close()`, so the return value is read from a closed cursor. Mainstream drivers tolerate this, but it is spec-questionable. Reference PR: #14341.

## Files and line ranges
- `django/core/cache/backends/db.py`
  - `delete()` lines 199–201 — delegates to `_base_delete_many([...])`, so it inherits the bug.
  - `delete_many()` lines 203–208 — builds key list, calls `_base_delete_many`, discards result (returns `None`).
  - `_base_delete_many()` lines 210–228 — the `with` block spans 219–227; the offending `return bool(cursor.rowcount)` is at 228.

Fix: capture the return value (or the `return`) inside the `with` block so `rowcount` is read while the cursor is open.

## Tests
- `tests/cache/tests.py`
  - `test_delete` (lines 334–340) asserts `cache.delete("key1") is True`.
  - `test_delete_nonexistent` (lines 342–343) asserts `False`.
  - `test_delete_many` (lines 556–559) only asserts no error; does not check a return value.
  - Versioning coverage: `test_cache_versioning_delete` (~line 812).
  - Dummy-backend `test_delete` (line 113) and `test_delete_many` (lines 203–210) are unrelated.

## Docs
`docs/topics/cache.txt` (database cache backend section) — the documented `delete()`/`delete_many()` return semantics should stay unchanged by the fix.

## Ruled out
- Not a driver-compatibility failure (major backends ignore the closed cursor).
- `delete_many()` returning `None` is intended; not part of the bug.
- No changes needed to `validate_key`/`make_key` paths.

## Conclusion
Behavioral fix is a one-line move of the `return` inside the `with` block in `_base_delete_many()`; existing tests at `tests/cache/tests.py:334` already cover the True/False return contract.
