# Handoff: LiveServerTestCase threaded DB connections

**Issue:** Intermittent `OperationalError: database "test_myapp" is being accessed by other users` during `destroy_test_db()` after `LiveServerTestCase`. Race: `ThreadedWSGIServer` request threads can still hold DB connections when test DB teardown begins.

**Mattering code:**
- `django/test/testcases.py:1476-1500` — `LiveServerThread`; `server_class = ThreadedWSGIServer` at line 1479; `connections_override` setup at 1481-1498.
- `django/test/testcases.py:1544` — `LiveServerTestCase.server_thread_class`; server creation/start at 1558-1590.
- `django/test/testcases.py:~1600-1612` — `_tearDownClassInternal()` calls `server_thread.terminate()` then `dec_thread_sharing()`.
- `django/core/servers/basehttp.py:62-82` — `WSGIServer` and `ThreadedWSGIServer`; `ThreadingMixIn` plus `daemon_threads = True` at 80-82. Daemon threads are not waited for on shutdown and may retain DB connections.
- `django/core/servers/basehttp.py:202-213` — `run()` also sets `daemon_threads=True` for threaded runserver; related pattern, not the test-server path.

**Tests/docs:**
- `tests/servers/test_liveserverthread.py` — `test_closes_connections` (lines 20-32) and `test_server_class` (line 34+) directly cover connection cleanup.
- `tests/servers/tests.py:98-151` — LiveServer/keep-alive behavior.
- Docs: `docs/topics/testing/tools.txt`, `LiveServerTestCase` section.

**Ruled out:** Non-threaded `WSGIServer` workaround avoided repro, confirming a threading/shutdown race rather than DB backend or `connections_override` bookkeeping alone. Keep-alive/content-length tests are not the root cause.

**Conclusion:** Fix belongs in `ThreadedWSGIServer`/`LiveServerThread` shutdown: ensure request threads close Django DB connections, or make shutdown wait for them (`daemon_threads=False`, join, or a `close_request`/`process_request_thread` hook). Re-run `tests/servers/test_liveserverthread.py` and `tests/servers/tests.py`.
