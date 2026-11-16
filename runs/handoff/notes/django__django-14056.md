## Handoff: `collectstatic` on missing `STATICFILES_DIRS`

**Issue:** `collectstatic` raises `OSError` when a `STATICFILES_DIRS` entry points to a missing directory. Desired behavior: emit a warning and continue.

**Relevant code**
- `django/contrib/staticfiles/finders.py`
  - `FileSystemFinder.__init__` (52–68): creates `FileSystemStorage` for every `STATICFILES_DIRS` root without checking existence.
  - `FileSystemFinder.check` (70–89): only validates list/tuple, `STATIC_ROOT` overlap, and prefix syntax; no missing-directory check.
  - `FileSystemFinder.list` (124–131): calls `utils.get_files(storage, ...)` for every location.
  - `AppDirectoriesFinder` (142–158) already guards with `os.path.isdir()` at line 154, so it is not the failing path.
- `django/contrib/staticfiles/utils.py` (16–39): `get_files()` calls `storage.listdir(location)` at line 23, which raises `OSError` for a missing directory.
- `django/contrib/staticfiles/management/commands/collectstatic.py` (86–105): iterates finders; no missing-directory handling.

**Tests/docs**
- `tests/staticfiles_tests/test_checks.py` (`FindersCheckTests`, especially 49–85): existing `staticfiles.E001`–`E003` coverage; add `W004`.
- `tests/staticfiles_tests/test_management.py` (`TestCollection`, 168+): add collectstatic coverage proving missing dirs warn and do not abort.
- `tests/staticfiles_tests/test_finders.py` (`TestFileSystemFinder`, 33–42).
- `docs/ref/checks.txt` staticfiles checks (~860–871); `docs/releases/4.0.txt` staticfiles section (~134).

**Ruled out:** `AppDirectoriesFinder` is already safe; changing `collectstatic` alone would leave other finder consumers broken. Existing E001–E003 checks do not cover existence.

**Conclusion:** Add `staticfiles.W004` warning in `FileSystemFinder.check()` for non-existent `STATICFILES_DIRS`, and skip those storages in `FileSystemFinder.list()` (e.g. `storage.exists('')`, matching the pattern at `finders.py:165/190`). This makes `collectstatic` warn and continue.
