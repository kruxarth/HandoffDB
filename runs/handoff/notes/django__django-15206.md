# Handoff: cache/debug decorators reject duck-typed requests

**Issue:** `cache_control`, `never_cache` (`django/views/decorators/cache.py`) and `sensitive_post_parameters` (`django/views/decorators/debug.py`) raise `TypeError` for any request that isn't an `HttpRequest` instance, breaking DRF, whose `rest_framework.request.Request` wraps rather than subclasses `HttpRequest`.

**Files and lines:**
- `django/views/decorators/cache.py`: line 3 (`HttpRequest` import), lines 32–36 (`cache_control` guard), lines 51–55 (`never_cache` guard).
- `django/views/decorators/debug.py`: line 3 (`HttpRequest` import), lines 80–84 (`sensitive_post_parameters` guard).

Each guard is `if not isinstance(request, HttpRequest): raise TypeError(...)`; the messages exist to hint at classmethod misuse (`@method_decorator`).

**Tests:**
- `tests/decorators/tests.py`: `NeverCacheDecoratorTest` (lines 499–545); specifically `test_never_cache_decorator_http_request` (line 523) and `test_cache_control_decorator_http_request` (line 537) assert the current `TypeError`. These must be rewritten to pass a duck-typed request and assert the cache headers are applied.
- `tests/view_tests/tests/test_debug.py`: `DecoratorsTests` (from line 1617), especially `test_sensitive_post_parameters_http_request` (lines 1639–1651).
- The `TypeError` assertions near lines 292 and 404 of `tests/decorators/tests.py` concern other decorators and are unrelated.

**Docs:** `docs/topics/http/decorators.txt` documents these decorators (not yet inspected in this session).

**Ruled out:** grepping `django/` found only these three `isinstance(request, HttpRequest)` checks. `cache_page` uses `CacheMiddleware` and is unaffected; `sensitive_variables` and the csrf/vary/clickjacking/http decorators have no request-type check. No existing duck-typed or DRF test coverage exists.

**Conclusion:** remove the three type guards and update the tests above to verify duck-typed requests work; the classmethod guidance they provided is lost and may need another channel.
