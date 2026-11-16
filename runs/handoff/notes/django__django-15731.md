## Handoff: `inspect.signature()` on manager methods

**Issue:** `inspect.signature(Person.objects.bulk_create)` returns `(*args, **kwargs)` instead of `(objs, batch_size=None, ignore_conflicts=False, update_conflicts=False, update_fields=None, unique_fields=None)`.

**Cause / files:**
- `django/db/models/manager.py`, `BaseManager._get_queryset_methods()` (lines 82–89). The generated `manager_method(self, *args, **kwargs)` (line 84) only copies `__name__` and `__doc__` (lines 87–88), so `inspect` sees the generic wrapper signature.
- `django/db/models/query.py`: `QuerySet.bulk_create()` at lines 745–753 has the correct signature; the queryset side is not at fault.
- The `queryset_only` filtering at `manager.py` lines 99–101 is unrelated to signature metadata.

**Tests:**
- `tests/custom_managers/tests.py`, especially `test_manager_use_queryset_methods` (line 79), and `tests/custom_managers/models.py` (`CustomQuerySet` line 35, `Person` line 98) are the natural place to add an `inspect.signature(Person.objects.bulk_create)` assertion.
- No existing tests use `inspect.signature` on managers (grep found only unrelated signature tests in `tests/signing/`, `tests/migrations/`, backends).
- Docs: `docs/topics/db/managers.txt` covers custom managers/`from_queryset`; may need no change.

**Ruled out:** Incorrect `bulk_create` definition; `queryset_only` filtering; manager class construction (`Manager.from_queryset`, `manager.py` line 116).

**Conclusion:** Replace manual `__name__`/`__doc__` assignment with `functools.wraps(method)(manager_method)` (import `functools`), preserving all metadata (`__wrapped__`, `__module__`, `__qualname__`, `__annotations__`) so `inspect.signature` unwraps to the QuerySet method. Repository is Django `4.2.dev20261116070157`, single snapshot commit; no patch applied yet.
