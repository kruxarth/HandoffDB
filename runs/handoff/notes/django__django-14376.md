# Handoff: MySQL backend uses deprecated `db` and `passwd` kwargs

## Issue
`django/db/backends/mysql/base.py` passes `db` and `passwd` to `mysqlclient`. mysqlclient deprecated these in favor of `database` and `password` (supported since 1.3.8; Django's minimum requirement is newer, so this is safe, and backportable to 2.2/3.1/3.2).

## Files and line ranges
- `django/db/backends/mysql/base.py`, `DatabaseWrapper.get_connection_params()` (~lines 193–220). The two relevant lines are ~202–205:
  - `kwargs['db'] = settings_dict['NAME']` → `kwargs['database']`
  - `kwargs['passwd'] = settings_dict['PASSWORD']` → `kwargs['password']`
- No other changes needed in the mysql backend.

## Tests
- `tests/backends/mysql/tests.py` currently only has `IsolationLevelTests`; no coverage of `get_connection_params()`. Add a test here asserting the returned params use `database`/`password` and not `db`/`passwd`.
- Follow the precedent in `tests/backends/postgresql/tests.py` lines ~117–145, which instantiate `DatabaseWrapper(settings).get_connection_params()` directly.
- `tests/backends/mysql/test_creation.py` uses `NAME`/`PASSWORD` settings dicts but is unrelated to connection kwargs.

## Docs
`docs/ref/databases.txt` (MySQL notes) and the release notes for the targeted versions; no user-facing API change, so documentation impact is minimal.

## Ruled out
- `grep` for `"db"`, `"passwd"`, `passwd=`, `db=` across `django/db/backends/mysql/` returned only `creation.py` methods (`_execute_create_test_db`, `_clone_test_db`), which are unrelated test-database naming helpers.
- No occurrences elsewhere in the mysql backend or its tests.

## Conclusion
Single two-line rename in `get_connection_params()` in `django/db/backends/mysql/base.py` (~202–205), plus a new regression test in `tests/backends/mysql/tests.py` modeled on the PostgreSQL backend's `get_connection_params()` tests.
