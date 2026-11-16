## Handoff note

**Issue:** `--parallel` fails when multiprocessing uses `spawn` (macOS/Windows): workers raise `AppRegistryNotReady` because they lack parent memory state, and cloned DB lookups fail because worker settings still contain the non-test database name.

**Key code:**
- `django/test/runner.py:365-376` — `get_max_test_processes()` returns `1` unless start method is `fork`, currently blocking parallel execution under `spawn`.
- `django/test/runner.py:394-412` — `_init_worker()` increments worker id and calls `connection.creation.setup_worker_connection(_worker_id)` but does not call `django.setup()` or repair the test DB name.
- `django/test/runner.py:426-443` — `ParallelTestSuite` and `init_worker` wiring.
- `django/test/runner.py:470-493` — pool initializer usage.
- `django/test/runner.py:874-883` — parallel suite construction.
- `django/db/backends/base/creation.py:257-268` and `django/db/backends/sqlite3/creation.py:51` — clone DB suffix naming.

**Tests/docs:**
- `tests/test_runner/test_discover_runner.py:46-92` — start-method mocks and spawn max-process test.
- `tests/test_runner/tests.py:483-525` — parallel/spawn management command tests.
- `tests/backends/sqlite/test_creation.py:20-36` — clone DB name coverage.
- `tests/runtests.py:372-395` — `parallel="auto"` and clone capability handling.
- `docs/ref/django-admin.txt:1490-1535` — parallel limitations; `docs/releases/4.0.txt:373-384`; `docs/internals/contributing/writing-code/unit-tests.txt:364`.

**Ruled out:** DB clone naming is not the root cause; `get_test_db_clone_settings()` correctly appends suffixes and is covered by SQLite tests. `parallel_type`/`auto` parsing also works.

**Conclusion:** Make `_init_worker()` spawn-safe by calling `django.setup()` and resetting each connection’s `NAME`/test DB name before `setup_worker_connection()`. Remove the fork-only early return in `get_max_test_processes()` and update spawn tests/docs.
