# Handoff: LazyObject advertises `__getitem__`/`__iter__` it may not have

**Issue:** `LazyObject` (and thus `SimpleLazyObject`, e.g. `request.user`) defines `__getitem__` and `__iter__` at class level, so `hasattr(obj, "__getitem__")`/`hasattr(obj, "__iter__")` return `True` even when the wrapped object doesn’t support them. Subsequent indexing/iteration raises `TypeError`.

**Key code — `django/utils/functional.py`:**
- `new_method_proxy()` lines 263–269: returns a function that lazily calls `_setup()` then delegates.
- `LazyObject` lines 272–383.
- `__getitem__ = new_method_proxy(operator.getitem)` line 369.
- `__iter__ = new_method_proxy(iter)` line 372.
- `SimpleLazyObject` lines 385+; the same proxies are inherited.
Because these are class attributes, `hasattr()` never touches `_wrapped`, which is the root cause.

**Tests:** `tests/utils_tests/test_lazyobject.py` — `lazy_wrap()` helper lines 24–33, `test_getattr` lines 35–37, and the `hasattr` parity assertion near line 400 (compares against another object, not the wrapped object). `tests/utils_tests/test_simplelazyobject.py` only covers pickling. Add regression tests wrapping a non-subscriptable/non-iterable object and asserting `hasattr()` parity with `_wrapped`.

**Docs:** `docs/releases/1.2.txt` lines 628–647 describe `LazyObject` magic-method behavior; `docs/releases/4.1.txt:301`; `docs/internals/contributing/writing-code/coding-style.txt` lines 336 and 353.

**Ruled out:** No other definitions outside `functional.py` (the `--include` greps failed under zsh — rerun with `find`/`xargs`). Repo is a single snapshot commit `3318059`, Django 4.1 alpha, so no upstream history to consult. `request.user`, admin, forms, etc. are consumers, not causes.

**Conclusion:** Root cause confirmed, not yet fixed. Remove or conditionally expose lines 369/372 so `hasattr()` reflects the wrapped object; assess backward-compatibility risk for code relying on lazy `__getitem__`/`__iter__`.
