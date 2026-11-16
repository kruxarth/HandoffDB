# Handoff: `path()`/`re_path()` should reject non-dict `kwargs`

## Issue
Passing a string as the third positional argument to `path()` (intending it as `name`) sets `kwargs="my_view"`. This doesn't fail at definition time; instead `resolve()` raises `ValueError: dictionary update sequence element #0 has length 1; 2 is required` (from `kwargs.update(self.default_args)`) and `reverse()` raises `AttributeError: 'str' object has no attribute 'items'`. The fix is to fail fast with a `TypeError` when `kwargs` is not a dict.

## Files that matter
- `django/urls/conf.py`: `_path()` at line 57; `kwargs` is forwarded to `URLPattern` at line 73. This is the correct validation point — add a check that `kwargs` is `None` or a `dict`, raising `TypeError` otherwise.
- `django/urls/resolvers.py`: `URLPattern.__init__` at line 343-344 stores `default_args`; `resolve()` at line 394 does `kwargs.update(self.default_args)`. This is where the confusing errors surface, but it's downstream — don't validate here.

## Tests
- `tests/urlpatterns/tests.py`: `SimplifiedURLTests`; existing `test_invalid_view`/`test_invalid_view_instance` (lines ~143-155) are the model for a new `test_invalid_kwargs`-style test.
- `tests/urlpatterns_reverse/tests.py`: `test_illegal_kwargs_message` (line 369), `view must be a callable` (line 1183).
- Note: `tests/urls_tests/` does **not** exist.

## Docs
- `docs/ref/urls.txt` documents `path()`/`re_path()` signatures and should note `kwargs` must be a dict.

## Ruled out
- A system check on `URLPattern`: rejected in favor of a direct `TypeError` in `_path()`.
- Guarding `name` type: out of scope for this issue (only `kwargs` is addressed).
- Validation in `resolvers.py`: wrong layer; error should occur at URLconf definition.

## Conclusion
Add a `TypeError` in `_path()` (`django/urls/conf.py`, ~line 57) when `kwargs` is not `None` and not a dict, plus a test in `tests/urlpatterns/tests.py` and a docs note in `docs/ref/urls.txt`.
