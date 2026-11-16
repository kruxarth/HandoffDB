# Handoff: dev server reloads on template changes

**Issue:** Django 3.2+ `runserver` restarts on any template edit; 3.1 did not. Reported as a regression, suspected to come from #25791 / PR 12928.

**Key code:**
- `django/template/autoreload.py:8-27` — `get_template_directories()` collects `DIRS` plus loader `get_dirs()`, filtering Django paths.
- `django/template/autoreload.py:29-34` — `reset_loaders()`.
- `django/template/autoreload.py:36-39` — `watch_for_template_changes()` calls `watch_dir(directory, '**/*')`, so every file in template dirs is watched, not just templates.
- `django/template/autoreload.py:41-48` — `template_changed()` returns `True` for any file under a template dir. That return value triggers the full autoreload.
- `django/utils/autoreload.py:21` — `file_changed` signal; `:267-295` — `watch_dir()`/`watched_files()` implement directory globs. No template-specific logic here.

**Tests:** `tests/template_tests/test_autoreloader.py:18-45` (`TemplateReloadTests`). `test_template_changed` explicitly asserts `True` and `reset_loaders` called; `test_non_template_changed` asserts `None`; `test_watch_for_template_changes` verifies glob watching.

**Docs:** `docs/releases/3.2.txt` documents that the development server now reloads on template changes; `docs/ref/django-admin.txt` covers `runserver` / `--noreload`.

**Ruled out:** core autoreload has no template handling; watchman is orthogonal; filesystem and app-directories loaders both expose `get_dirs`; Jinja2 is skipped by the `isinstance(DjangoTemplates)` check; cached loader is irrelevant under `DEBUG`. The broad `'**/*'` glob explains why non-template files in template dirs also reload.

**Conclusion:** intended behavior introduced by PR 12928, not a regression. If loader reset without restart is desired, change `template_changed` to call `reset_loaders()` and return `False`, then update `test_template_changed`.
