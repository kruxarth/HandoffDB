## Handoff: PostgreSQL passfile support for `dbshell`

**Issue:** `dbshell` for PostgreSQL still exposes passwords via `PGPASSWORD`/process environment; it should support `.pgpass`/`PGPASSFILE` instead of relying on `PGPASSWORD`.

**Key files/lines:**
- `django/db/backends/postgresql/client.py`: `DatabaseClient.settings_to_cmd_args_env()` builds `psql` args and sets `env['PGPASSWORD']` around line 40. This is the main change point.
- `django/db/backends/base/client.py`: `BaseDatabaseClient.runshell()` (~lines 21–25) merges `env` with `os.environ` and calls `subprocess.run()`. Any passfile mechanism must fit this args/env interface or extend it.
- `django/core/management/commands/dbshell.py`: `handle()` (~lines 25–45) delegates to `connection.client.runshell()`; no direct password handling.
- `django/db/backends/mysql/client.py`: already supports `read_default_file` and uses `MYSQL_PWD`; useful comparison but not the target.

**Tests/docs:**
- `tests/dbshell/test_postgresql.py`: current assertions expect `{'PGPASSWORD': ...}` at lines ~18–30 and ~80–105. These must change for passfile behavior.
- `tests/dbshell/tests.py`, `tests/dbshell/fake_client.py`: generic `dbshell` command coverage.
- `docs/ref/databases.txt` lines ~118–146 cover PostgreSQL `OPTIONS`/service files; document passfile/`PGPASSFILE` there if exposed.
- `docs/ref/django-admin.txt` lines ~202–243 document `dbshell`.

**Ruled out:** MySQL/Oracle/SQLite backends are out of scope for this PostgreSQL-specific issue. No existing `PGPASSFILE`/`passfile` references were found; only `PGPASSWORD` at `postgresql/client.py:40` and its tests.

**Conclusion:** The gap is confirmed in `postgresql/client.py`. Next step is to implement temporary `.pgpass`/`PGPASSFILE` handling through the client args/env path, update `test_postgresql.py`, and document it.
