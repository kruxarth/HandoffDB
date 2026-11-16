## Handoff note

**Issue:** `LogoutView` performs an unnecessary intermediate redirect when `?next=` contains an unsafe URL. With `LOGOUT_REDIRECT_URL` configured, `POST /logout/?next=http://evil/` redirects to `/logout/`, then to the configured URL, instead of redirecting directly.

**Relevant code:** `django/contrib/auth/views.py:117-179`, especially `LogoutView.get_next_page()` at `155-179`. The problematic fallback is around line 178: when `url_has_allowed_host_and_scheme()` rejects the user-supplied `next`, the code sets `next_page = self.request.path` (i.e. `/logout/`). That causes the extra round-trip. The logic predates `LOGOUT_REDIRECT_URL`; the unsafe value should be ignored and the view should fall back to `LOGOUT_REDIRECT_URL`/`self.next_page` directly, or otherwise return `None` without redirecting to the current path.

**Tests:** `tests/auth_tests/test_views.py:1152-1210` (`LogoutTest`), particularly redirect tests around `1194-1210`; URL patterns in `tests/auth_tests/urls.py:94-102`. Add a regression test asserting an unsafe `next` with `LOGOUT_REDIRECT_URL` set produces a single redirect to the configured URL.

**Docs:** `docs/ref/settings.txt` (`LOGOUT_REDIRECT_URL`) and `docs/topics/auth/default.txt` (`LogoutView`).

**Ruled out:** The security check itself is working; this is not a redirect-validation bypass. User-visible final destination is correct. The GET-logout deprecation and `auth_logout()`/session clearing are unrelated.

**Conclusion:** Fix the unsafe-`next` fallback in `get_next_page()` to avoid redirecting to `request.path`; preserve the safe-URL validation and configured redirect behavior.
