## Handoff: ASGI request body closed prematurely

**Issue:** PR #15675 caused `I/O operation on closed file` when a view reads `request.body`. The ASGI handler closes the request body file before the view/response runs.

**Key code:**
- `django/core/handlers/asgi.py:175,198` — `body_file.close()` calls. These run too early; the body file is the backing store for `ASGIRequest._stream`, so `request.body` later fails.
- `django/core/handlers/asgi.py:290` — response close via `sync_to_async`; relevant to ordering/lifetime.
- `django/core/handlers/base.py:141,163` — `response._resource_closers.append(request.close)`; this is response cleanup, not the cause.
- `django/http/request.py:322-344` — `HttpRequest.body` reads `self._stream` into `_body`.
- `django/http/request.py:388-391` — `HttpRequest.close()` only closes uploaded files in `_files`; it does **not** close `_stream`/`body_file`.
- `django/http/request.py:401-404` — `read()` sets `_read_started`.

**Tests/docs:**
- `tests/asgi/tests.py` — `ASGITest`, uses `ApplicationCommunicator`; add a regression test where a view accesses `request.body`.
- `tests/asgi/urls.py` — views are defined inline here; add a body-reading view/URL.
- `docs/ref/request-response.txt` — documents `HttpRequest.body`; `docs/howto/deployment/asgi/` covers ASGI deployment.

**Ruled out:** `HttpRequest.close()` / `base.py` resource closers are not closing the ASGI body stream. `_read_started`/`_body` caching logic is not the culprit; WSGI is unaffected.

**Conclusion:** Defer `body_file.close()` until after the response is produced/sent (or on disconnect/exception paths only). Add an ASGI test that reads `request.body` in a view to prevent regression.
