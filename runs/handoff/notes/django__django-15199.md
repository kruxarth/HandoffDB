## Handoff note

**Issue:** Deprecate `cached_property`’s `name` argument (Django 4.0+), since it was only required for Python 3.5.

**Relevant code**
- `django/utils/functional.py:7-38` — `cached_property` class. `__init__` at line 26 still accepts `name=None`; the argument is effectively unused because `__set_name__` (lines 30-38) derives the name. The docstring at lines 14-15 already says the argument is obsolete and “will be deprecated in Django 4.0 (#30127).”
- Imports at `django/utils/functional.py:1-4` lack `warnings` and deprecation warning imports.

**Tests**
- `tests/utils_tests/test_functional.py:83-104` — `test_cached_property`; line 100 uses `cached_property(other_value, name='other')`.
- `tests/utils_tests/test_functional.py:106-131` — `test_cached_property_auto_name`; line 122 uses `name='different_name'`.
- Related tests at lines 133-183 cover reuse and `__set_name__` errors. Add `assertWarnsMessage(RemovedInDjango50Warning, ...)` coverage for the `name` argument and adjust/remove uses at lines 100 and 122.

**Docs**
- `docs/ref/utils.txt:429` — signature `cached_property(func, name=None)` should be updated and deprecation noted.
- `docs/ref/models/instances.txt:144` only references `@cached_property`; likely no change.

**Ruled out**
- No `RemovedInDjango40Warning` exists in this checkout; `django/utils/deprecation.py:8-12` defines `RemovedInNextVersionWarning` and `RemovedInDjango50Warning`, and `django/__init__.py:3` reports version `4.1.0 alpha`. Use `RemovedInDjango50Warning`.
- No in-tree production calls to `cached_property(..., name=...)` under `django/`.
- Git history is only a snapshot, so no prior deprecation commit to follow.

**Conclusion:** Implement a `RemovedInDjango50Warning` in `cached_property.__init__` when `name is not None`, update the two test uses/assertions, and revise the `docs/ref/utils.txt` signature/deprecation text.
