# Handoff: incorrect “Synchronous middleware … adapted” log message

**Issue:** Debug logging for middleware adaptation is inverted. The docs promise “Synchronous middleware … adapted” for synchronous middleware, but the current implementation logs “Asynchronous middleware … adapted” (and vice versa). Middleware functionality itself is correct; only log wording is wrong.

**Key files/lines:**
- `django/core/handlers/base.py:53-57` — `load_middleware()` passes `name='middleware %s' % middleware_path` to `adapt_method_mode()`.
- `django/core/handlers/base.py:104-132` — `adapt_method_mode()` treats `name` as the method name. In the `is_async` branch it logs `"Synchronous %s adapted."`; in the `elif method_is_async` branch it logs `"Asynchronous %s adapted."`. With a middleware name these labels are reversed. Fix should track `method_name` separately: when `name` is provided, log “Asynchronous” in the first branch and “Synchronous” in the second; when `name` is absent, preserve existing method messages.
- `tests/middleware_exceptions/tests.py:222-234` — `test_async_middleware` currently asserts the buggy `"Synchronous middleware ... adapted."` for an async middleware.
- `tests/middleware_exceptions/tests.py:260-300` — sync/async middleware log assertions around lines 268 and 298 also encode the inverted expectations.
- `tests/middleware_exceptions/middleware.py` — defines `async_payment_middleware` and related test middleware.
- `docs/topics/async.txt` — warning documenting the expected “Synchronous middleware … adapted” message.

**Ruled out:** Middleware loading order, async/sync adaptation behavior, and the docs are not the problem. No functional middleware regression was found; the issue is confined to `adapt_method_mode()` logging.

**Conclusion:** Apply the proposed `adapt_method_mode()` change to distinguish middleware names from method names, then update the middleware-exception tests to expect “Asynchronous middleware … adapted.” for async middleware and “Synchronous middleware … adapted.” for sync middleware.
