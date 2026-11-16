**Handoff note: async `View` GET returns sync `HttpResponseNotAllowed`**

**Issue:** An async `View` subclass with only `async def post()` crashes on GET with `TypeError: object HttpResponseNotAllowed can't be used in 'await' expression`. `as_view()` marks the view coroutine-based because `view_is_async` is true, but the dispatch fallback returns a synchronous response.

**Key code:** `django/views/generic/base.py`
- `View.view_is_async` at lines 63-65 detects any async HTTP handler.
- `as_view()` at lines 119-120 sets `view._is_coroutine`, so the whole view is treated as async.
- `dispatch()` at lines 138-141 selects `self.http_method_not_allowed` when the method is absent.
- `http_method_not_allowed()` at lines 144-151 returns `HttpResponseNotAllowed(...)` synchronously.
- `options()` at lines 153-163 already wraps its response in an async `func()` when `view_is_async`; this is the model for the fix.

**Tests/docs:** Add regression coverage in `tests/views/tests_base.py` (View dispatch/as_view behavior), with async-view coverage in `tests/async/tests.py`. Relevant docs: `docs/ref/class-based-views/base.txt` and `docs/topics/async.txt`.

**Ruled out:** `django/views/decorators/http.py:26-42` (`require_http_methods`) has a similar synchronous 405 response but is not on this class-based-view path. `django/core/handlers/base.py:106-129` (`adapt_method_mode`) correctly detects coroutine functions; the handler itself is the problem. No asgiref/ASGI adapter change is needed.

**Conclusion:** Fix `http_method_not_allowed()` to return an awaitable response when `self.view_is_async`, matching the existing `options()` pattern at `base.py:159-163`, and add the async GET regression test.
