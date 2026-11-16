# Handoff: `handler500` as a class-based view raises `urls.E007`

## Issue
Assigning `handler500 = MyView.as_view()` triggers `SystemCheckError: (urls.E007) ... does not take the correct number of arguments (request)` during `manage.py check`. Function-based handlers work; the 500 handler with a CBV fails.

## Key files and lines
- `django/urls/resolvers.py:424-452` — `_check_custom_error_handlers()`. Lines 428 defines `(400,2),(403,2),(404,2),(500,1)`. Lines 438-441 do `inspect.signature(handler)` then `signature.bind(*[None] * num_parameters)`. Lines 443-451 build the `urls.E007` error.
- `django/views/generic/base.py:49-79` — `View.as_view()`; lines 75 and 79 call `update_wrapper`, which sets `__wrapped__` to `cls.dispatch`. `inspect.signature()` follows this, so the visible signature is `(self, request, *args, **kwargs)`, not `(request)`.

## Tests
- `tests/check_framework/test_urls.py:169-190` — `CheckCustomErrorHandlersTests.test_bad_handlers`, asserts four `urls.E007` errors with argument counts `[2,2,2,1]`.
- Fixtures: `tests/check_framework/urls/bad_error_handlers.py`, `good_error_handlers.py`, `bad_error_handlers_invalid_path.py`.
- `tests/urlpatterns_reverse/tests.py:1059-1093` — handler400/404/500 tests.
- `tests/generic_views/test_base.py` — `as_view()` wrapping/signature behavior.

## Docs
`docs/releases/4.0.txt` and `docs/releases/3.2.txt` were searched; no relevant entry. `docs/ref/urls.txt` is the natural place to document the fix.

## Ruled out
- Not in `django/urls/resolver.py`; the file is `django/urls/resolvers.py`.
- Not caused by handler import failures (`urls.E008`) or the CSRF check in `django/core/checks/security/csrf.py`, which uses the same signature-binding pattern but is unrelated.

## Conclusion
Confirmed bug: the check binds `num_parameters` positional placeholders without accounting for the bound `self` in CBV signatures. For 400/403/404, `self` + `request` coincidentally matches two placeholders; for 500, only one placeholder is bound, so `bind()` fails. Fix `_check_custom_error_handlers()` to detect `handler.view_class`/`as_view()` and validate the underlying `dispatch` signature without `self`, or otherwise bind CBVs with an extra argument. Add a CBV fixture and a regression test in `tests/check_framework/test_urls.py`.
