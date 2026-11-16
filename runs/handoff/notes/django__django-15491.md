## Handoff: CSRF failure view charset

**Issue:** `csrf_failure()` renders `CSRF_FAILURE_TEMPLATE_NAME` with an explicit `content_type="text/html"`, so the HTTP `Content-Type` omits `charset`. UTF-8 templates can render incorrectly despite the inline template’s `<meta charset>` at `django/views/csrf.py:19`.

**Mattering files/lines:**
- `django/views/csrf.py:160` — `HttpResponseForbidden(t.render(c), content_type="text/html")`. This explicit content type suppresses Django’s default charset handling.
- `django/http/response.py:110-116` — when `content_type=None`, `HttpResponse` sets `text/html; charset={self.charset}`.
- `django/http/response.py:152-161` — `charset` derives from an existing `Content-Type`; passing `text/html` without a charset leaves the header charset-less.
- The inline template’s `<meta http-equiv="content-type" ... charset=utf-8>` does not fix the HTTP header.

**Tests/docs:**
- `tests/view_tests/tests/test_csrf.py` — `CsrfViewTests`, especially translation tests around lines 18-40 and custom-template tests around lines 99-119. Add a regression assertion here for the `Content-Type` charset.
- `tests/csrf_tests/tests.py:314` uses `response.charset` but is not directly about this failure page.
- `tests/flatpages_tests/test_csrf.py` and `tests/check_framework/test_security.py` reference CSRF failure behavior but not this header issue.
- No matching entry found in `docs/releases/4.1.txt` or `4.0.txt`.

**Ruled out:** `HttpResponse` charset machinery is not broken; it correctly appends `DEFAULT_CHARSET` when `content_type` is omitted. The inline `<meta>` tag is insufficient because it is body-level.

**Conclusion:** Fix `django/views/csrf.py:160` by omitting `content_type` or passing `text/html; charset={settings.DEFAULT_CHARSET}`. Add a test in `tests/view_tests/tests/test_csrf.py` asserting the response `Content-Type` includes the charset.
