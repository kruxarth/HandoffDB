## Handoff: `method_decorator()` should preserve wrapper assignments

**Issue:** Decorators applied via `method_decorator()` receive a `functools.partial` object lacking `__name__`, `__module__`, etc. A decorator doing `wraps(func)` / reading `func.__name__` raises `AttributeError: 'functools.partial' object has no attribute '__name__'`.

**Relevant code — `django/utils/decorators.py`:**
- Line 3: imports `partial`, `update_wrapper`, `wraps`.
- Lines 13–19: `_update_method_wrapper()` — "cheats" by decorating a dummy function and calling `update_wrapper(_wrapper, dummy)` to copy attributes onto the wrapper *after* decoration. This does not help decorators that inspect `__name__` during decoration.
- Lines 22–53: `_multi_decorate()` builds `bound_method` as a `partial` bound to `method`; that partial is what gets handed to each decorator, hence the missing attributes. `method_decorator()` itself is at line 53.

**Root cause:** `bound_method` is a bare `partial`; `update_wrapper()` is never applied to it before the decorators run.

**Ruled out / verified:** `update_wrapper()` on a `functools.partial` works fine (`__name__`, `__doc__` get set), and arbitrary attributes can be assigned to a partial. So the fix is to apply `update_wrapper(bound_method, method)` before invoking decorators in `_multi_decorate()`, making `__name__`, `__module__`, `__qualname__`, `__doc__`, `__annotations__`, `__wrapped__` available. `_update_method_wrapper`'s dummy trick likely becomes redundant/adjustable.

**Tests:** `tests/decorators/tests.py` — helper decorators lines 160–195; `MethodDecoratorTests` line 198; `test_preserve_signature` (202), `test_preserve_attributes` (210), `test_new_attribute` (274), `test_descriptors` (308), and `__name__` assertion at line 272. Add a regression test using a `@wraps`-based decorator that reads `func.__name__`.

**Docs:** `docs/topics/class-based-views/intro.txt` and `docs/ref/utils.txt` (method_decorator section) may need no change, but check for notes on wrapper attributes.

**Conclusion:** Fix in `_multi_decorate()` by wrapping the partial with `update_wrapper` prior to decoration.
