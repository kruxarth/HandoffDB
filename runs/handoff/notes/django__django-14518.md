## Handoff: CSRF token error message source

**Issue:** `CsrfViewMiddleware` rejection messages for bad request CSRF tokens should state whether the token came from POST data or the configured CSRF header.

**Code:** `django/middleware/csrf.py`
- Lines 31–39: reason constants (`REASON_CSRF_TOKEN_*`, `REASON_INCORRECT_LENGTH`, `REASON_INVALID_CHARACTERS`).
- Lines 116–126: `InvalidTokenFormat` and `_sanitize_token()`; the exception carries only a reason, not the token source.
- Lines 318–358: `_check_token()`. The request token is read from `request.POST['csrfmiddlewaretoken']` around line 337, else from `request.META[settings.CSRF_HEADER_NAME]` around line 349. Format errors are caught at lines 354–356 and converted to `RejectRequest(f'CSRF token {exc.reason}.')`. This call site knows the source, so the source label should be added here (or passed into `InvalidTokenFormat`).

**Tests:** `tests/csrf_tests/tests.py`
- Lines 34–66: `CsrfViewMiddlewareTestMixin` helpers, including `_get_POST_request_with_token()`.
- Lines 118–157: `_check_bad_or_missing_token()` and tests expecting the old messages at lines 143, 150, and 157; these must be updated.
- Line 224 covers `X-CSRFToken` with PUT/DELETE and is relevant for header-source coverage.

**Docs:** A grep of `/work/repo/docs` found no references to these exact message strings; no docs update appears necessary unless behavior is documented elsewhere.

**Ruled out:** Cookie-side token errors (separate “CSRF cookie …” messages) are out of scope. Missing-token message (`REASON_CSRF_TOKEN_MISSING`) is also separate. No other files reference the exact strings.

**Conclusion:** Implement source-aware messages in `_check_token()` at the POST/header extraction points, then update the three expected strings and add header-path assertions in `tests/csrf_tests/tests.py`.
