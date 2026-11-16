## Handoff: template autoreload regression with empty string in `TEMPLATES["DIRS"]`

**Issue:** Since the pathlib normalization from ticket #32744 (commits 68357b2, c0d506f), a `DIRS` entry of `""` (e.g. `os.getenv(...).split(",")`) becomes the project root. `template_changed()` then returns `True` for every file change, so app-code autoreload never fires.

**Key code:**
- `django/template/autoreload.py:10-31` — `get_template_directories()`: `items.update(cwd / to_path(dir) for dir in backend.engine.dirs)` turns `''` into `cwd`, and `watch_dir(cwd, "**/*")` watches the whole project.
- `django/template/autoreload.py:43-46` — `watch_for_template_changes()` registers those dirs.
- `django/template/autoreload.py:~48-56` — `template_changed()` matches any path under a watched dir, hence always `True`.
- `django/utils/_os.py:56-62` — `to_path("")` returns `Path("")` == `Path(".")`; root cause of the normalization.
- `django/template/backends/base.py:20` — `self.dirs = list(params.pop("DIRS"))` stores `''` unvalidated; `django/template/backends/django.py:27` passes it to `Engine`.

**Tests:** `tests/template_tests/test_autoreloader.py` (`TemplateReloadTests.test_template_changed`, `test_non_template_changed`) is the place for a `DIRS=[""]` regression test; `tests/utils_tests/test_autoreload.py` covers `watch_dir`/`file_changed`. Docs: `docs/ref/settings.txt` (TEMPLATES/DIRS) and `docs/topics/templates.txt`.

**Ruled out:** Non-`DjangoTemplates` backends are already skipped; loader `get_dirs()` handling and `watch_dir` itself (`django/utils/autoreload.py:285`) are fine. Prior Windows reports (#32630, #33266, #33285) are the same empty-string cause, not platform-specific.

**Conclusion:** Filter empty/invalid `DIRS` entries before `cwd / to_path(...)` (or when building `self.dirs`), and add the regression test asserting `template_changed()` is falsy for non-template paths with `DIRS=[""]`.
