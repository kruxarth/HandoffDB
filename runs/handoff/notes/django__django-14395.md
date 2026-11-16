## Handoff: CacheHandler.all initializes unused caches

**Issue:** After commit `98e05cc`, `CacheHandler.all()` became eager: it iterates every configured `CACHES` alias and calls `self[alias]`, instantiating unused backends. With custom diskcache backends this causes I/O lag. The reporter’s patch made `all()` return only already-created connections.

**Relevant code:**
- `django/utils/connection.py:53-61` — `BaseConnectionHandler.__getitem__()` lazily creates and stores a connection in thread-local `_connections`.
- `django/utils/connection.py:69-70` — `__iter__()` yields all configured aliases.
- `django/utils/connection.py:72-73` — `all()` is now `[self[alias] for alias in self]`, so it forces creation of every configured backend.
- `django/core/cache/__init__.py:26-49` — `CacheHandler` inherits `all()`.
- `django/core/cache/__init__.py:52-59` — `close_caches()` calls `caches.all()` on `request_finished`, so every request initializes every cache just to close it.

**Tests/docs:**
- `tests/cache/tests.py:2584` — `CacheHandlerTest` covers instance reuse, thread locality, and invalid aliases/backends; it does not cover `.all()` or close-time initialization.
- `tests/cache/tests.py:398`, `:1440`, `:1721` — existing `test_close` cases do not assert lazy initialization.
- `tests/utils_tests/test_connection.py:1-10` — only tests `create_connection()` abstraction.
- `docs/topics/cache.txt` — public cache API documentation.

**Ruled out:** The bug is not in `__getitem__` caching or thread-local storage; `__getitem__` still behaves lazily. It is not cache-backend-specific.

**Conclusion:** Do not globally revert `all()` to only-initialized semantics. Add an `initialized_only=False` parameter to `BaseConnectionHandler.all()` (returning only entries present in `self._connections` when true), and change `close_caches()` to use `caches.all(initialized_only=True)`. Add a regression test that a configured-but-unused cache is not instantiated by `close_caches()`, while an initialized cache is closed.
