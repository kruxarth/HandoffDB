## Handoff note: admin catch-all view ignores `FORCE_SCRIPT_NAME`

**Issue:** `AdminSite.catch_all_view()` redirects using `request.path_info`, which excludes the script name. With `FORCE_SCRIPT_NAME` (or any `SCRIPT_NAME`), the redirect drops the prefix.

**Relevant code**
- `django/contrib/admin/sites.py:293-294` — appends the final catch-all URL pattern when `final_catch_all_view` is enabled.
- `django/contrib/admin/sites.py:419-429` — `catch_all_view()`; line 423 is the bug: `path = '%s/' % request.path_info` should use `request.path` so the script name is preserved. It is decorated with `no_append_slash` at line 419 and checks `APPEND_SLASH` at line 421.
- `django/core/handlers/wsgi.py:64-82` and `django/http/request.py:145-149` — `WSGIRequest` correctly builds `request.path` from `SCRIPT_NAME` + `PATH_INFO`; `path_info` intentionally excludes the script name.

**Tests**
- `tests/admin_views/tests.py:6534-6715` — existing catch-all / `final_catch_all_view=False` and missing-slash redirect tests.
- `tests/admin_views/test_adminsite.py:43-46` — related `SCRIPT_NAME` handling in `each_context()`.
- `tests/requests/tests.py:128-151` — verifies `FORCE_SCRIPT_NAME` populates `request.path` correctly.

**Docs**
- `docs/ref/contrib/admin/index.txt` — documents `AdminSite.final_catch_all_view` / admin URLs.
- `docs/ref/settings.txt` — `FORCE_SCRIPT_NAME`.

**Ruled out:** `FORCE_SCRIPT_NAME` parsing in WSGI/ASGI and `WSGIRequest.path` construction are correct; the test client sets `PATH_INFO`/`SCRIPT_NAME` normally. The defect is isolated to the admin catch-all redirect target.

**Conclusion:** Change `django/contrib/admin/sites.py:423` to use `request.path` instead of `request.path_info` (matching PR 14404), and add an admin test covering `FORCE_SCRIPT_NAME` redirects.
