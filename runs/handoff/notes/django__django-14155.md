## Handoff: `ResolverMatch.__repr__` and `functools.partial`

**Issue:** `ResolverMatch.__repr__()` shows `func=functools.partial` for partial views, hiding the underlying view and bound arguments.

**Key code:**
- `django/urls/resolvers.py:32-64` — `ResolverMatch.__init__()`/`__repr__()`. `self.func = func` at line 34; `_func_path` is built at lines 48-53. For a `functools.partial`, the no-`__name__` fallback uses `func.__class__`, producing `functools.partial`. `__repr__()` at lines 62-64 prints `_func_path`.
- `django/urls/resolvers.py:363` — `URLPattern.resolve()` creates `ResolverMatch(self.callback, ...)`.
- `django/urls/resolvers.py:371-374` — `URLPattern.lookup_str` already unwraps `functools.partial`, but this does not affect `ResolverMatch.__repr__`.
- `django/urls/resolvers.py:574` — nested resolver construction also passes `sub_match.func`.

**Tests/fixtures:**
- `tests/urlpatterns_reverse/tests.py:1106-1145` — `ResolverMatchTests`; `test_repr()` at lines 1140-1145 only covers a normal view.
- `tests/urlpatterns_reverse/tests.py:32-75` — `resolve_test_data` has no partial cases.
- `tests/urlpatterns_reverse/views.py:59-61` — existing `empty_view_partial`, `empty_view_nested_partial`, `empty_view_wrapped`.
- `tests/urlpatterns_reverse/urls.py:62-64` — existing `/partial/`, `/partial_nested/`, `/partial_wrapped/` patterns.
- Docs: `docs/ref/urlresolvers.txt` (`ResolverMatch` API section).

**Ruled out:** `URLPattern.lookup_str` partial handling is separate and already correct; `get_callable()` returns callables unchanged. The bug is isolated to `ResolverMatch` deriving `_func_path` from the partial object.

**Conclusion:** Unwrap `functools.partial` in `ResolverMatch.__init__()` before computing `_func_path` (and likely `self.func`) so `repr()` names the underlying view. Add a `test_repr()` case using the existing partial URL fixtures; preserve `args`/`kwargs` behavior for bound partial arguments.
