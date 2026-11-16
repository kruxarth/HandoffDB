# Handoff: multiple values in `X-Forwarded-Proto`

**Issue:** `SECURE_PROXY_SSL_HEADER` handling compares the header value exactly, so a proxy chain sending `X-Forwarded-Proto: https,http` is treated as non-secure. The header should be parsed as a comma-separated list (leftmost = original client entry point) and the secure value matched against it.

**Key code:** `django/http/request.py`, lines 252–265 (`HttpRequest.scheme`). Line 262 fetches `header_value`; line 264 does `header_value == secure_value` — the exact-match comparison is the defect. The fix belongs here: split on `,`, strip whitespace, and compare the leftmost value to `secure_value`. `is_secure()` (line 267) and `_current_scheme_host` (line 241) depend on this, so behavior propagates to CSRF and absolute-URL generation.

**Tests:** `tests/settings_tests/tests.py`, class `SecureProxySslHeaderTest`, lines 404–436 — extend with comma-separated cases (e.g. `"https,http"` secure, `"http,https"` not secure, whitespace variants). Related coverage: `tests/view_tests/tests/test_csrf.py:38-44`, `tests/middleware/tests.py:449`, `tests/sitemaps_tests/test_https.py:42`, `tests/requests/tests.py:1060` (header mapping only).

**Docs:** `docs/ref/settings.txt`, lines 2412–2442 (`SECURE_PROXY_SSL_HEADER` description) should note that only the first value of a comma-separated header is considered. Also referenced at `docs/topics/security.txt:137,145` and `docs/ref/middleware.txt:251,450`.

**Ruled out:** No literal `x-forwarded-proto` exists in Python sources; the header name is user-configured via the setting. The setting is `None` by default (`django/conf/global_settings.py:457`), so no change is needed there. The `ValueError`/`ImproperlyConfigured` path (lines 257–261) is about tuple unpacking and is unrelated. Recent release notes (`docs/releases/2.2.3.txt:21`, `1.11.22.txt:20`) only document prior `scheme` behavior, not this parsing.

**Conclusion:** Implement list parsing in `HttpRequest.scheme`, taking the leftmost non-empty value, plus tests and a settings-doc clarification.
