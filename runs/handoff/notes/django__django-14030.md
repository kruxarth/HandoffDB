## Handoff: Admin `never_cache` on instance methods

**Issue:** `AdminSite.login`, `logout`, and `password_change` are instance methods decorated directly with `@never_cache`. This passes `self` (the `AdminSite`) as the decorator’s `request` argument. `never_cache` still works because it only mutates the response, but decorators that inspect the request (e.g. `require_http_methods`) fail with `AttributeError: 'CustomAdminSite' object has no attribute 'method'`.

**Key files/lines:**
- `django/contrib/admin/sites.py`
  - line 21: imports `never_cache`
  - lines 360, 382, 517: direct `@never_cache` on `login`, `logout`, and `password_change`
  - line 234: `admin_view()` already applies `never_cache(inner)` to wrapped views
- `django/utils/decorators.py`: `method_decorator` is the appropriate wrapper for instance methods.

**Tests/docs:**
- `tests/admin_views/tests.py`
  - `NeverCacheTests` around lines 4424–4500 checks `Cache-Control`/max-age for admin index, login, logout, password change, etc.
  - login/logout behavior around lines 1617–1785 and `AdminViewLogoutTests` around line 5901.
- `tests/admin_views/test_adminsite.py` covers custom `AdminSite` URL setup.
- `tests/decorators/tests.py` around lines 474–480 covers `never_cache` itself.
- No admin docs reference this decorator usage directly.

**Ruled out:** This is not a cache-header bug: existing `NeverCacheTests` pass because `never_cache` ignores the first argument except when calling the view. The failure only appears with request-dependent decorators.

**Conclusion:** Replace direct `@never_cache` on the affected instance methods with `method_decorator(never_cache)` (importing `method_decorator`), or otherwise ensure the decorator receives the actual request. Add a regression test using a request-dependent decorator on a custom `AdminSite` method to confirm `self` is no longer passed as `request`.
