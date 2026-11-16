# Handoff: AdminSite.catch_all_view() drops query string in APPEND_SLASH redirects

## Issue
`AdminSite.catch_all_view()` redirects `/admin/auth/foo?id=123` to `/admin/auth/foo/`, dropping `?id=123`. Expected: `/admin/auth/foo/?id=123`. Introduced by #31747.

## Root cause / relevant code
- `django/contrib/admin/sites.py:447-457` — `catch_all_view()`. Line 456 builds the redirect from `request.path` (path only, no query string):
  ```python
  return HttpResponsePermanentRedirect("%s/" % request.path)
  ```
  This is the defect. `request.get_full_path(force_append_slash=True)` would preserve the query string and append the slash.
- `django/contrib/admin/sites.py:310-311` — where the catch-all pattern is registered (`final_catch_all_view`).
- `django/contrib/admin/sites.py:69` — `final_catch_all_view = True`.
- `django/middleware/common.py:76-96` (`get_full_path_with_slash`) and `django/http/request.py` `get_full_path()` — the canonical approach for building APPEND_SLASH redirects, including `escape_leading_slashes()` protection. The fix should mirror this.

## Tests / docs
- Tests: `tests/admin_views/test_templatetags.py` not relevant; the admin catch-all behavior is tested in `tests/admin_views/tests.py` (grep for `catch_all_view` / `final_catch_all_view`). Add a regression test asserting the query string is preserved in the redirect for `APPEND_SLASH=True`.
- Docs: `docs/ref/contrib/admin/index.rst` (`final_catch_all_view`) and `docs/ref/settings.txt` (`APPEND_SLASH`).

## Ruled out
- `CommonMiddleware.should_redirect_with_slash()` / `get_full_path_with_slash()` already handle query strings correctly; the admin view is `@no_append_slash` and bypasses that middleware path, so the bug is local to `catch_all_view`.
- `django/contrib/flatpages/views.py:42` has the same `"%s/" % request.path` pattern but is a separate issue (flatpage fallback), not the reported one.

## Conclusion
Fix line 456 in `django/contrib/admin/sites.py` to use `request.get_full_path(force_append_slash=True)` (escaped via `escape_leading_slashes`), preserving query strings. Add a regression test.
