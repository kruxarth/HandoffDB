## Handoff: `startproject` should honor umask

**Issue:** `startproject`/`startapp` copy template permissions wholesale, so files ignore the user's umask. With `umask 077`, generated `settings.py` was still `0644`, and read-only template caches (Zero Install) failed on write.

**Key code:**
- `django/core/management/templates.py:184-185` — `TemplateCommand.handle()` calls `shutil.copymode(old_path, new_path)` then `self.make_writeable(new_path)`. This is the root cause: `copymode()` copies every permission bit from the template, bypassing umask.
- `django/core/management/templates.py:348` — `make_writeable()` adds owner write for read-only templates; keep this behavior for Zero Install.
- `django/core/management/commands/startproject.py:1-23` and `startapp.py` only delegate to `TemplateCommand`; no local permission logic.
- `django/conf/project_template/manage.py-tpl` is mode `0755`; app/project text templates are `0644`. Naive `copymode()` therefore makes `manage.py` executable but also leaks template modes onto all files.

**Tests:** `tests/admin_scripts/tests.py:1978-2300` (`StartProject`, especially `test_simple_project` around 1996) and `tests/admin_scripts/management/commands/custom_startproject.py`. No existing umask/copymode assertions in `admin_scripts`; add a regression test setting `umask(0o077)` and checking generated `settings.py` is not group/world-readable while `manage.py` stays executable.

**Docs:** `docs/ref/django-admin.txt:1241-1282` (`startapp`) and `1332-1359` (`startproject`); release note in `docs/releases/4.1.txt`.

**Ruled out:** `django/core/files/storage.py:247-253` and `django/core/cache/backends/filebased.py:117-123` already manage umask but are unrelated. `django/utils/_os.py` has no permission handling.

**Conclusion:** Fix belongs in shared `TemplateCommand.handle()`: stop copying full mode; preserve only the executable bit when the source is executable, and let normal file creation honor umask. This fixes both `startproject` and `startapp`.
