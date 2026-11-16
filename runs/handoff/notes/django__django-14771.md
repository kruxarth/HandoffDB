# Handoff: autoreload does not propagate `-X` options

**Issue** On Windows, `python -X utf8 manage.py runserver` starts the autoreloader child without `-X utf8`; `open()` then uses `cp936`. `--noreload` works because no child process is spawned.

**Code** `django/utils/autoreload.py`: `get_child_arguments()` around lines 215–260 builds the child command. Line 222 copies only `sys.warnoptions` as `-W...`; there is no equivalent for `sys._xoptions`. Line 260 launches the child with `subprocess.run`. `django/core/management/commands/runserver.py:108` calls `autoreload.run_with_reloader`.

**Tests** `tests/utils_tests/test_autoreload.py`, `TestChildArguments` lines 170–246. `test_warnoptions` at lines 199–203 is the closest template. Add cases mocking `sys._xoptions`, including `True` values (`-Xutf8`) and string values (`-Xutf8=0`). Existing subprocess tests around lines 469–470 mock `sys.warnoptions`.

**Docs** No doc change likely needed. `docs/ref/django-admin.txt` covers `runserver`/autoreload but not `-X`.

**Ruled out** File-watching/stat reloader logic, settings/app import behavior, and `-m`/script-path argument handling. `--noreload` succeeding confirms the defect is child-argument construction. `-W` propagation already works.

**Conclusion** In `get_child_arguments()`, append CPython `-X` arguments from `sys._xoptions` alongside the existing `-W` arguments at line 222: `True` becomes `-Xname`, string values become `-Xname=value`. Add regression tests in `TestChildArguments`.
