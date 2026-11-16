## Handoff: Deprecate `make_random_password()`

**Issue:** `BaseUserManager.make_random_password()` is unused since `fcd837cd0f9b2c706bc49af509628778d442bb3f` and should be deprecated.

**Code that matters:**
- `django/contrib/auth/base_user.py:33-45` — `BaseUserManager.make_random_password()`. This is the only implementation. If deprecating, add a `RemovedInDjango51Warning` (this repo is Django 4.2 alpha; see `django/utils/deprecation.py:8-17`) and keep the method for the deprecation period. `get_random_string` is imported at line 14 and is used by this method.
- `django/contrib/auth/base_user.py:14` — import only needed while the method remains.

**Docs:**
- `docs/topics/auth/customizing.txt:773-786` — public API documentation for `make_random_password()`. Add a deprecation note.
- `docs/releases/4.2.txt:245-251` — “Features deprecated in 4.2” section. Add an entry describing the deprecation and removal in Django 5.1.

**Tests:**
- `tests/auth_tests/test_models.py:167-172` — `test_make_random_password()` exercises the method. Update it to assert the deprecation warning (or otherwise accommodate the warning) rather than leaving it as a plain behavioral test.

**Ruled out:** A repo-wide grep for `make_random_password` found only the four matches above: implementation, docs, release-notes-adjacent docs, and one test. No other Django code calls it. No `RandomPassword` variants were found. No auth module currently imports `RemovedInDjango51Warning`, so that import will need to be added.

**Conclusion:** Deprecate `BaseUserManager.make_random_password()` with `RemovedInDjango51Warning`, document the deprecation in `customizing.txt` and `4.2.txt`, and update the existing test to expect the warning.
