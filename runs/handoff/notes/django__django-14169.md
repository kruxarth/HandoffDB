# Handoff: SQLite clone test DB filenames get an extra dot

## Issue
`get_test_db_clone_settings()` in `django/db/backends/sqlite3/creation.py` builds cloned on-disk test database names with an extra dot when `--parallel` is used (`test_db_1..sqlite3`), or a trailing dot when the source name has no extension (`test_db_1.`).

## Key code
`django/db/backends/sqlite3/creation.py`, `get_test_db_clone_settings()`, lines 51-58. Line 57 uses `os.path.splitext()`, which already returns the extension *with* its leading dot. Line 58 then formats with `'{}_{}.{}'`, inserting a second dot. The fix is the one-character change to `'{}_{}{}'`. The in-memory branch (lines 54-55) returns the original settings untouched, so it is unaffected. `_clone_test_db()` (lines 60-66) consumes the name but does not construct it; no change needed there.

## Tests
`tests/backends/sqlite/test_creation.py` (16 lines) currently only covers `test_db_signature()` via `TestDbSignatureTests.test_custom_test_name`; it has **no** coverage of clone naming or `get_test_db_clone_settings()`. A regression test should be added here asserting the clone name for both `db.sqlite3`-style and extension-less names. `tests/backends/mysql/test_creation.py:47-54` shows the existing pattern for clone tests (`_clone_test_db('suffix', ...)`).

## Ruled out
The in-memory path (early return, line 54) and `_clone_test_db()` were ruled out as causes. No existing SQLite test exercises cloning, so nothing previously caught the bug; the MySQL clone tests are unrelated to filename formatting.

## Conclusion
Confirmed single-source formatting bug, present since the `--parallel` feature landed. Fix line 58 and add a naming regression test to `tests/backends/sqlite/test_creation.py`. Docs for SQLite test databases (`docs/ref/databases.txt`) are worth a skim but likely need no edit.
