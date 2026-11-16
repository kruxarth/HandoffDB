## Handoff: CSRF cookie token format rejection

**Issue:** `CsrfViewMiddleware.process_view()` should reject a malformed CSRF *cookie* token before `_get_token()` generates a new token/mask that is guaranteed not to match. This mirrors #32795 for the non-cookie token.

**Files/lines:**
- `django/middleware/csrf.py:35-39` — `REASON_INCORRECT_LENGTH` / `REASON_INVALID_CHARACTERS`.
- `django/middleware/csrf.py:116-126` — `InvalidTokenFormat` and `_sanitize_token()`.
- `django/middleware/csrf.py:222` — `process_request()` catches `InvalidTokenFormat` from `_get_token()` and creates a new token; this behavior should remain.
- `django/middleware/csrf.py` around `380-412`, especially `406` — `process_view()` already rejects a malformed request token via `_sanitize_token()`. The cookie-token `_get_token()` call needs analogous handling: let `InvalidTokenFormat` bubble and reject with `CSRF token {exc.reason}.` before `_compare_masked_tokens()`.

**Tests:** `tests/csrf_tests/tests.py:132-142` already checks invalid characters/incorrect length for the request token. Add analogous cookie-token cases; verify the rejection happens before new token generation and uses the specific reason string. Existing missing-cookie behavior (`REASON_NO_CSRF_COOKIE`) should stay unchanged.

**Docs:** `docs/ref/csrf.txt` and `docs/howto/csrf.txt` relate to CSRF middleware behavior; no docs change is likely needed unless the rejection message is documented.

**Ruled out:** The non-cookie token path is already handled by the `InvalidTokenFormat` catch at `csrf.py:406`; `process_request()` should continue to recover by issuing a new token. Missing-cookie handling is separate.

**Conclusion:** Implement by allowing `InvalidTokenFormat` from `_get_token()` to propagate, handling it differently in `process_request()` (new token) and `process_view()` (reject early). No code changes were made in this investigation.
