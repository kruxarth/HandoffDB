## Handoff note

**Issue:** `CsrfViewMiddleware.process_response()` misuses `csrf_cookie_needs_reset` and `response.csrf_cookie_set`, so `_set_token()` can run twice when the response cookie was already set, and the cookie can fail to reset when a reset is required.

**Key code:** `django/middleware/csrf.py`
- Lines 439–451: `process_response()` early-return logic. The current condition checks `request.csrf_cookie_needs_reset` and `response.csrf_cookie_set` in a way that conflates “already set” with “must reset”.
- Line 450: sets `response.csrf_cookie_set = True`.
- Lines 113, 226, 378: set `request.csrf_cookie_needs_reset = True`; these are the producers that `process_response()` must honor.
- `_set_token()` is called from this block and is the side effect at risk of duplicate/missed execution.

**Tests:** `tests/csrf_tests/tests.py`
- `test_process_response_get_token_not_used` around line 155.
- `test_process_response_get_token_used` around line 1124.
- `test_session_modify` around line 1132 covers unchanged-cookie/session behavior.
Related fixtures/views: `tests/csrf_tests/views.py`, `tests/csrf_tests/csrf_token_error_handler_urls.py`, and `tests/csrf_tests/test_context_processor.py`. No dedicated regression test for these two flags was found.

**Docs:** `docs/ref/csrf.txt` and `docs/howto/csrf.txt` document `CsrfViewMiddleware`/`ensure_csrf_cookie`; neither documents the internal flags.

**Ruled out:** No production references to either flag outside `django/middleware/csrf.py`. The issue is not in the session-save path or test-only CSRF disabling; `test_session_modify` and the existing `process_response` tests do not exercise the bug.

**Conclusion:** The early-return condition is wrong. It should return early only when the response cookie is already set **and** no reset is needed; when `csrf_cookie_needs_reset` is true, `_set_token()` must run regardless of the `CSRF_COOKIE_NEEDS_UPDATE`/`CSRF_COOKIE_USED` checks. Add regression tests for both double-set and missed-reset cases.
