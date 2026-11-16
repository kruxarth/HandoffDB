## Handoff: dev server won’t restart when `BASE_DIR` is in `TEMPLATES[0]['DIRS']`

**Issue:** Adding `BASE_DIR` to template `DIRS` makes `runserver` stop detecting any file changes, not just `settings.py`.

**Cause:** `django/template/autoreload.py`
- `get_template_directories()` (lines 12–32) correctly includes `BASE_DIR` as a watched template dir.
- `watch_for_template_changes()` (lines 43–46) watches it recursively with `**/*`.
- `template_changed()` (lines 49–54) treats every changed file under a template dir as a template change: it calls `reset_loaders()` and returns `True`. With `BASE_DIR` in `DIRS`, every project `.py` change hits this path, so the autoreloader is suppressed.

**Ruled out:** `django/utils/autoreload.py` watch/stat mechanics; `watch_dir()` behavior covered by `tests/utils_tests/test_autoreload.py:565-651`; template directory collection in `get_template_directories()`; and a settings-specific bug.

**Tests:** `tests/template_tests/test_autoreloader.py:1-60` (`TemplateReloadTests`). Existing `test_non_template_changed` uses a `.py` path outside template dirs, so it misses this. Add a regression test where `DIRS=[BASE_DIR]` and a `.py` file under it returns `None` / does not reset loaders; a real template file should still reset.

**Docs:** `docs/ref/settings.txt` (`TEMPLATES` / `DIRS`) and `docs/ref/django-admin.txt` (`runserver` autoreload).

**Conclusion/fix:** In `template_changed()` (`django/template/autoreload.py:49-54`), ignore Python files before resetting loaders or returning `True` (e.g. return `None` for `.py`), so project Python changes are handled by the normal autoreloader even when `BASE_DIR` is a template dir.
