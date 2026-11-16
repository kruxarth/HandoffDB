# Handoff note

**Issue:** Technical 404 debug page renders CBV view names as `<class 'view_tests.views.Http404View'>` instead of `view_tests.views.Http404View`. Regression from commit `0c0b87725bbcffca3bc3a7a2c649995695a5ae3b`.

**Key files/lines:**
- `django/views/debug.py:513-558` — `technical_404_response()`. The view-name/`caller` computation near lines 540-555 derives the name from `resolver_match.func`. For `View.as_view()` this resolves to the wrapper function, and the code ends up using the class object/repr instead of the CBV class name. This is the root cause.
- `django/views/templates/technical_404.html:41` — only renders `{{ caller }}` under “Raised by:”; ruled out as the source.
- `tests/view_tests/views.py:75-77` — `Http404View` fixture.
- `tests/view_tests/urls.py:33` — `classbased404/` route.
- `tests/view_tests/tests/test_debug.py:189-192` — `test_classbased_technical_404`, which asserts the exact expected string `view_tests.views.Http404View`; lines 171-187 cover the function-view case. Run/update these tests.
- Docs: `docs/ref/views.txt` documents `technical_404_response()`; `docs/howto/custom-error-pages.txt` is related background.

**Ruled out:** Template rendering, URL resolution (the route resolves correctly), and exception handling. Module-prefix calculation is fine; only the CBV class representation is wrong.

**Conclusion:** Fix the `caller` derivation in `technical_404_response()` to unwrap the CBV class (e.g. via `func.view_class` / `__qualname__` or `__name__`) rather than using the class object’s repr. Verify with `test_classbased_technical_404` and the function-view test.
