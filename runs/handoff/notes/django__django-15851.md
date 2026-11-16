## Handoff: dbshell parameters must precede dbname on PostgreSQL

**Issue:** `./manage.py dbshell -- -c "select ..."` produced `psql: warning: extra command-line argument "-c" ignored` because psql requires all options before the database name.

**Root cause / files:**
- `django/db/backends/postgresql/client.py`, `DatabaseClient.settings_to_cmd_args_env`, lines 10–37. Lines 26–28 default `dbname` to `"postgres"`; lines 29–34 add `-U`, `-h`, `-p`; **lines 35–36 append `dbname`**; **line 37 appends `parameters`** — wrong order. Fix: move `args.extend(parameters)` to just before the `if dbname:` block (i.e. after the port handling at line 34), leaving dbname last.
- `django/db/backends/base/client.py` lines 23–28: `runshell()` delegates to `settings_to_cmd_args_env()` then `subprocess.run()` — no ordering logic here, no change needed.
- `django/core/management/commands/dbshell.py` lines 24–30: collects trailing `parameters` (`nargs="*"`) and passes them to `runshell()`; unchanged.

**Tests:** `tests/dbshell/test_postgresql.py` — `test_basic` (lines 19–34) asserts `["psql","-U","someuser","-h","somehost","-p","444","dbname"]` with no parameters; add a case passing `parameters=["-c","select 1;"]` asserting they come before `dbname`. Sibling suites `tests/dbshell/test_mysql.py`, `test_sqlite.py`, `test_oracle.py` cover the other backends.

**Docs:** `docs/releases/1.9.7.txt` (prior dbshell PostgreSQL fix precedent); `docs/ref/django-admin.txt` documents `dbshell` parameters.

**Ruled out:** MySQL (`mysql/client.py`), Oracle (`oracle/client.py` lines 22–26, already appends parameters after connect string), and SQLite (`sqlite3/client.py` line 9) — this ordering requirement is psql-specific; their tests need no changes. The `import signal` at `postgresql/client.py` line 1 is unused but out of scope.

**Conclusion:** Reorder args in the PostgreSQL client only so `parameters` precede `dbname`; add a regression test in `tests/dbshell/test_postgresql.py`. Repo version 4.2.0 alpha.
