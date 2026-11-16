# Handoff: `ResolverMatch` is not pickleable

**Issue:** `pickle.loads(pickle.dumps(resolve(path)))` works for function-based views but raises `PicklingError` for class-based views (`MyView.as_view()`) and `contrib.admin` views. `ResolverMatch.func` holds a closure; pickle's `save_global` finds a module+name match but fails the identity check.

**Files/lines that matter:**
- `django/urls/resolvers.py:32-70` — `ResolverMatch.__init__` stores the raw callable in `self.func`; `_func_path` (lines 50-55) is computed only for `__repr__`, not reused for pickling. This is the fix site.
- `django/urls/resolvers.py:387` — `URLPattern.resolve()` constructs the match from `self.callback`.
- `django/urls/resolvers.py:395-402` — existing view-path logic (handles `functools.partial`, `view_class`, `__qualname__`).
- `django/views/generic/base.py:48-78` — `as_view()` returns a local `view` closure; comment at 73-75 notes `__name__`/`__qualname__` are intentionally unchanged.
- `django/contrib/admin/sites.py:225+` — `admin_view()` returns an `inner` closure wrapper-named after the real view, causing the identity mismatch.
- `django/test/client.py:729-733, 921-925` — test client attaches `SimpleLazyObject(lambda: resolve(...))`, also unpicklable.

**Ruled out:** `get_callable` LRU cache (`django/urls/utils.py`), urlconf import mechanics, and `SimpleLazyObject` as sole cause — failure reproduces with plain `pickle.dumps(resolve(...))`, and FBV matches already pickle.

**Conclusion:** Make `ResolverMatch` itself serializable in `django/urls/resolvers.py` by serializing the view via the already-computed `_func_path` (e.g. `__reduce__`/`__getstate__`/`__setstate__`) and resolving it back on load, instead of pickling the closure in `func`.

**Tests:** add cases to `tests/urlpatterns_reverse/tests.py:1108` (`ResolverMatchTests`), using `tests/urlpatterns_reverse/views.py:38-43` (`ViewClass`/`view_class_instance`) and `namespace_urls.py:26-29`; optionally `tests/test_client/tests.py:195`.

**Docs:** `docs/releases/4.0.txt:353-356` (URLs section is a placeholder) — add a release note.
