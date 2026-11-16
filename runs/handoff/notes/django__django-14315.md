## Handoff: dbshell ignores `os.environ` (PostgreSQL)

**Issue:** `dbshell` for PostgreSQL passes an empty environment to `subprocess.run`, dropping inherited `os.environ` (e.g. `PGHOST`, `PGUSER`). Regression from commit `bbe6fbb` / PR #14315.

**Root cause & key lines:**
- `django/db/backends/postgresql/client.py:39` initializes `env = {}`; `:54` returns `(args, env)` — always a dict, even when no `PGPASSWORD`/`PGSERVICE`/SSL options are set.
- `django/db/backends/base/client.py:22-26` (`runshell`): `args, env = self.settings_to_cmd_args_env(...)`; then `if env: env = {**os.environ, **env}`. Since `{}` is falsy, the merge is skipped and `subprocess.run(args, env={}, check=True)` is called with an empty env, so `os.environ` is never inherited.

**Related code:** `mysql/client.py:10,57` correctly starts with `env = None`; `oracle/client.py:27` and `sqlite3/client.py:10` return `None`. So PostgreSQL is the outlier — behavior is correct for all other backends.

**Tests:** `tests/dbshell/test_postgresql.py` (asserts `settings_to_cmd_args_env` output — should expect `None` env when no options), `tests/dbshell/tests.py` (`test_command_missing`), plus `test_mysql.py`, `test_sqlite.py`, `test_oracle.py` as references. Docs: `docs/ref/django-admin.txt` (`dbshell`) and `docs/ref/databases.txt`.

**Ruled out:** MySQL/Oracle/SQLite clients (already return `None`); the merge logic in `base/client.py` itself is fine when `env` is non-empty — only the truthiness check mishandles `{}`.

**Conclusion:** Fix by making PostgreSQL return `None` when no env vars are needed (build `env` conditionally, matching MySQL), and/or change `base/client.py` to `if env is not None`. Add a PostgreSQL test asserting `None` env with plain settings and a dict when `PASSWORD`/`service`/SSL options are supplied.
