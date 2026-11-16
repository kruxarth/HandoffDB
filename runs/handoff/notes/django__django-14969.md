## Handoff note: `has_perms()` accepting a bare string

**Issue:** `user.has_perms("foobar")` silently iterates the string's characters instead of raising. Fix: raise `TypeError` when `perm_list` is a `str`; non-string iterables (tuple, set, generator) must keep working.

**Code that matters:**
- `django/contrib/auth/models.py:302-307` — `PermissionsMixin.has_perms()`, the primary site. Add the `isinstance(perm_list, str)` guard and raise `TypeError` before the `all(...)` comprehension. This is the only implementation that needs changing.
- `django/contrib/auth/models.py:454` — a second `has_perms` definition; check whether it needs the same guard or delegates.
- `django/contrib/auth/models.py:287-300` — `has_perm()`, the single-permission sibling; useful precedent and shows why silently delegating a string here is a bad habit.
- `django/contrib/auth/backends.py:124-133` — existing `isinstance(perm, str)` / `TypeError` pattern to match in style and message wording.
- `tests/auth_tests/models/custom_user.py:61` — overridden `has_perms` in a test model; confirm it isn't affected.

**Tests:** `tests/auth_tests/test_auth_backends.py` — `BaseBackendTest.test_has_perm` (line 51), `BaseModelBackendTest.test_custom_perms` (line 108), `RowlevelBackendTest.test_has_perm` (line 440), and `AnonymousUserBackendTest.test_has_perms` (line 475). Add the new assertion near `test_has_perm`. `tests/auth_tests/test_models.py` has `UserWithPermTestCase` (line 303) as another candidate.

**Docs:** `docs/ref/contrib/auth.txt:225` (`has_perms` signature) and `docs/topics/auth/customizing.txt:957`; `docs/topics/auth/default.txt:345` shows a tuple example. Note the behavior change in the docstring.

**Ruled out:** changing `AnonymousUser`, `has_perm()`, the backends, or coercing strings to single-permission calls.

**Conclusion:** guard in `PermissionsMixin.has_perms()` only; all existing `has_perms` callers pass lists/tuples and are unaffected.
