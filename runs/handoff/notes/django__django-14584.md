# Handoff: Add database alias to `django.db.backends` log records

**Issue:** SQL DEBUG logs from the `django.db.backends` logger omit the database alias, which is essential when using database routing. Reference PR #11994.

**Relevant code:**
- `django/db/backends/utils.py`: logger defined at line 11; `CursorDebugWrapper` at lines 92–130; the actual log call is `logger.debug(...)` at line 123 inside `debug_sql`. This is where the `alias` should be added to the `extra` context (available as `self.db.alias`).
- `django/db/backends/base/base.py` lines 586–590: `cursor()` returns `CursorDebugWrapper` when `queries_log`/debug is enabled; confirms `self.db` is the connection wrapper.

**Docs:** `docs/ref/logging.txt` lines ~160–185 document the `django.db.backends` extra context (`duration`, `sql`, `params`). Add `alias` here. Possibly note in `docs/releases/4.0.txt`.

**Tests:** `tests/backends/tests.py` (e.g. `LastExecutedQueryTest` around line 52), `tests/backends/test_utils.py`, and `tests/backends/base/test_base.py`. Add an `assertLogs('django.db.backends', 'DEBUG')` test checking `record.alias`.

**Ruled out:** `creation.py` `self.log(... 'alias %s')` calls (test-database creation messages, not query logging); `django/db/backends/postgresql/base.py:323` (`alias=` passed to psycopg2, unrelated); `sqlite3/schema.py:116` and `sqlite3/features.py:113` (`atomic(alias)`); `ddl_references.py:218`.

**Conclusion:** Fix is localized to the `logger.debug` call in `CursorDebugWrapper.debug_sql` in `django/db/backends/utils.py`, adding `'alias': self.db.alias` to the logging extra dict, with a matching docs update and a logging-assertion test.
