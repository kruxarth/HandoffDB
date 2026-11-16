## Handoff note

**Issue:** Autoreload reconstructs the child command incorrectly for `python -m foo.bar.baz`. `get_child_arguments()` uses `__main__.__spec__.parent`, so `foo.bar.baz` becomes `-m foo.bar`.

**Key code:** `django/utils/autoreload.py`, `get_child_arguments()` lines **213–228**. The faulty branch is **226–228**:
- Line 226 checks `__main__.__spec__` and truthiness of `.parent`.
- Line 227 appends `['-m', __main__.__spec__.parent]`.
- Line 228 appends `sys.argv[1:]`.

For `-m foo.bar.baz`, `__spec__.parent` is `foo.bar`; for package execution such as `-m foo.bar`, the parent is correctly `foo.bar`. Any fix must preserve package `.__main__` handling while keeping the full dotted module name for non-package modules.

**Tests:** `tests/utils_tests/test_autoreload.py`, `TestChildArguments` lines **166–229**, especially:
- `test_run_as_module` lines **170–174** (Django package).
- `test_run_as_non_django_module` lines **176–182** (package `utils_tests.test_module`).

Related fixtures: `tests/utils_tests/test_module/__main__.py`, plus `tests/utils_tests/test_module/child_module/grandchild_module.py` for a dotted-module scenario. No documentation files were identified as relevant in this investigation.

**Ruled out:** `__main__.__spec__` being absent/Conda environments and Windows executable resolution are separate fallbacks at lines **229–234**; module/file watching logic in `iter_modules_and_files()` and null-byte path handling are unrelated.

**Conclusion:** The bug is isolated to using `__spec__.parent` instead of the full `__spec__.name`. The fix should reconstruct `-m` with the full module name, stripping a trailing `.__main__` only for package execution, and add a regression test for `python -m foo.bar.baz`.
