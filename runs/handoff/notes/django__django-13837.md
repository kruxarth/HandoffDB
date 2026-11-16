## Handoff note: autoreload for `python -m <other_pkg> runserver`

**Issue:** `django.utils.autoreload.get_child_arguments()` only recognizes `python -m django runserver` by comparing `sys.argv[0]` with `django.__main__.__file__`. This fails for `python -m pkg_other_than_django runserver`, and also fails where modules lack `__file__`. The child process should be relaunched with the actual `-m` package.

**Code:** `django/utils/autoreload.py`, `get_child_arguments()` lines 213–241. Key lines:
- 219–220: imports `django.__main__` and builds `django_main_path` from `__file__`.
- 221: `py_script = Path(sys.argv[0])`.
- 224–227: compares paths and hardcodes `['-m', 'django']`.
- 228–241: Windows/nonexistent-`sys.argv[0]` handling must be preserved.

**Fix direction:** Replace the `__file__` comparison with `__main__.__spec__`. When `__main__.__spec__` is not `None` and `__main__.__spec__.parent` is non-empty, relaunch using `['-m', __main__.__spec__.parent, *sys.argv[1:]]`. Do not use `__main__.__package__`; it is usually but not always equal to `__spec__.parent`.

**Tests:** `tests/utils_tests/test_autoreload.py`, especially `get_child_arguments` assertions at lines 164, 172, 183, 194, and 203. The test module imports `django.__main__` at line 20; update/remove that import if no longer needed. Add cases for another package’s `__main__.__spec__.parent` and for `__spec__ is None`.

**Docs:** Related context is in `docs/ref/django-admin.txt` (runserver/autoreload behavior) and `docs/howto/custom-management-commands.txt` (Django-based CLI utilities). No broad docs change appears necessary unless the supported invocation is documented.

**Ruled out:** Comparing `__file__` (not available in all Python environments), relying on `__package__`, and detecting only the literal `-m django`. Keep the existing Windows executable/script-entrypoint fallback.

**Conclusion:** Implement the `__main__.__spec__.parent` check; this supports any `-m` package and avoids `__file__`.
