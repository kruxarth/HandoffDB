# Handoff: ResolverMatch repr incorrect for CBVs

## Issue
`repr(resolve('/redirect/'))` for a class-based view renders `func=urlpatterns_reverse.views.view` instead of `urlpatterns_reverse.views.LazyRedirectView`. Regression since 4.0 (#32260 removed `update_wrapper` from `View.as_view()` and deliberately left `__name__`/`__qualname__` unset).

## Root cause
`django/urls/resolvers.py`, `ResolverMatch.__init__` (lines 33–57). The branch at lines 49–54 keys off `hasattr(func, '__name__')`; `as_view()` returns a function literally named `view`, so it has `__name__` and takes the function-based path, producing `...views.view`. `self._func_path` (line 54) then feeds `view_name` (line 56) and `__repr__` (lines 62–72).

Related: `django/views/generic/base.py` lines 67–75 — `view.view_class = cls` at line 70, with the comment at 73–74 stating `view_class` is the robust way to name the view.

## Fix
Mirror the `lookup_str` logic already correct at `django/urls/resolvers.py` lines ~400–412: if `hasattr(func, 'view_class')`, rebind `func = func.view_class` before the `__name__` check (same shape as the #33425 patch).

## Tests
Add `test_classbased_repr` to `ResolverMatchTests` in `tests/urlpatterns_reverse/tests.py` (class at line 1109; existing repr tests at lines 1145–1166). Fixtures: `tests/urlpatterns_reverse/views.py` lines 46–47 (`LazyRedirectView`), `tests/urlpatterns_reverse/reverse_lazy_urls.py` line 9. Also verify `tests/generic_views/test_base.py::test_resolve_view` still passes.

## Ruled out
Not in `as_view()` itself (intentional), nor in `lookup_str`, `django/views/debug.py` lines 547–548, or `django/contrib/admindocs/utils.py` lines 23–27 — all already `view_class`-aware. `match.func` is still the correct callable; only `_func_path`/`view_name`/`repr` are wrong. No docs change needed (`ResolverMatch` repr isn't specified in `docs/ref/urlresolvers.txt`).
