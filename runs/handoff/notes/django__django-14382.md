## Handoff note

**Issue:** `django-admin startapp name directory/` fails with `CommandError: '' is not a valid app directory...` because shell tab-completion adds a trailing slash.

**Root cause / code:** `django/core/management/templates.py:77` calls:
`self.validate_name(os.path.basename(target), 'directory')`
For `target='directory/'`, `os.path.basename()` returns `''`, so validation fails. `validate_name()` at `django/core/management/templates.py:211-236` is behaving correctly; it rejects the empty string. The fix should strip trailing separators before basename, e.g. `os.path.basename(target.rstrip(os.sep))`, preserving existing identifier validation.

**Tests:** `tests/admin_scripts/tests.py` is the relevant suite. `StartApp` begins around line 2150; existing `test_invalid_name` covers invalid identifiers. Add a regression test for `startapp` with a trailing-slash directory there. Also note `test_template_dir_with_trailing_slash` around line 2013 covers related trailing-slash handling for templates/projects, not this `startapp` directory validation.

**Docs:** `docs/ref/django-admin.txt` documents `startapp`/`startproject` directory arguments; inspect/update only if the behavior needs clarification. No docs were changed in this investigation.

**Ruled out:** `validate_name()` itself is not defective; it correctly rejects an empty name. This is not specific to `startapp`’s command class because the faulty call is in shared `TemplateCommand`, so `startproject` may be affected too.

**Conclusion:** Normalize `target` by removing trailing path separators before calling `basename()` at `templates.py:77`, then add a focused regression test in `tests/admin_scripts/tests.py`.
