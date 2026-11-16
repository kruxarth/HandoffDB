# Handoff: SimpleLazyObject missing `__radd__`

**Issue:** `SimpleLazyObject` does not proxy `__radd__`, so expressions like `other + lazy_obj` fail even when the wrapped object supports addition.

**Relevant code:**
- `django/utils/functional.py:263-268` — `new_method_proxy()`, the standard lazy proxy helper.
- `django/utils/functional.py:352-374` — existing proxied dunder methods on `LazyObject`; this is the right area for an explicit `__radd__`.
- `django/utils/functional.py:385` — `SimpleLazyObject`, which inherits `LazyObject`.

**Tests:**
- `tests/utils_tests/test_lazyobject.py:23-300` — `LazyObjectTestCase`, inherited by `SimpleLazyObjectTestCase`.
- `tests/utils_tests/test_lazyobject.py:301-423` — `SimpleLazyObjectTestCase`; add a regression test here or in the inherited base class so both lazy types are covered. Existing comparison tests start around line 62.
- `tests/utils_tests/test_simplelazyobject.py:1-16` — only covers pickling, not relevant to this fix.

**Docs:** `docs/ref/utils.txt` documents `LazyObject`/`SimpleLazyObject`; update only if it enumerates proxied operations.

**Ruled out:**
- `__radd__ = new_method_proxy(operator.radd)` — `operator.radd` does not exist.
- `__radd__ = new_method_proxy(operator.attrgetter("__radd__"))` — wrapped types may not define `__radd__`, and `attrgetter` does not suppress `AttributeError`.

**Conclusion:** Add an explicit `__radd__` to `LazyObject` near the other dunder proxies in `django/utils/functional.py:352-374`: call `_setup()` when `_wrapped is empty`, then return `other + self._wrapped`. Add a regression test covering an unevaluated and evaluated `SimpleLazyObject`. No broader proxy rewrite is needed.
