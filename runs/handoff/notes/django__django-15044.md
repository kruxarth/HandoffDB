# Handoff: CacheMiddleware thread safety

Issue: `UpdateCacheMiddleware`, `FetchFromCacheMiddleware`, and single-class `CacheMiddleware` persist `self.cache = caches[cache_alias]` in `__init__`, sharing one cache backend object across request threads. With pylibmc/uWSGI threaded this reproduces `pylibmc.ConnectionError` under concurrent requests.

Key code in `django/middleware/cache.py`:
- `UpdateCacheMiddleware` ~53-105; `__init__` stores backend, `process_response` uses `self.cache`.
- `FetchFromCacheMiddleware` ~108-160; `__init__` stores backend; `process_request` line 145 calls `get_cache_key(..., cache=self.cache)`.
- `CacheMiddleware` ~177-190; line 186 is the reported assignment.

Tests/docs: `tests/cache/tests.py` middleware tests at ~998-1022, 2002-2025, and 2157-2221 exercise fetch/update behavior but not concurrent access; `tests/cache/tests_async.py` also relates. Docs: `docs/topics/cache.txt` middleware section and `docs/ref/settings.txt` for `CACHE_MIDDLEWARE_ALIAS`.

Ruled out: cache-key construction, `@cache_page`/`get_cache_key` logic, and `Cache-Control`/timeout handling. The failure is shared backend connection/state, not key generation.

Conclusion: root cause confirmed as per-middleware-instance cache backend sharing. Fix should avoid persisting the backend object on the middleware instance—resolve `caches[self.cache_alias]` per request/response, or use a thread-local/lazy accessor—and add a threaded regression test covering middleware `process_request`/`process_response` for all three classes.
