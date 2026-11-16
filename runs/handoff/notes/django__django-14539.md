# Handoff: `urlize()` escaped entity + trailing punctuation

**Issue:** `urlize('Search for google.com/?q=1&lt! and see.')` returns an anchor ending in `&lt` but leaks `lt!` outside the link. Expected link text is `google.com/?q=1&lt`, with `!` as trailing punctuation and href containing `%3C`.

**Files/lines:**
- `django/utils/html.py:236` — `urlize()` is the primary suspect. Its trailing-punctuation/entity handling splits `&lt` across the anchor boundary.
- `django/utils/html.py:200-232` — `smart_urlquote()` ruled out; href quoting (`%3C`) is correct.
- `django/template/defaultfilters.py:342,349` — `urlize`/`urlizetrunc` filters delegate to the utility; tests here may also need coverage.

**Tests:**
- `tests/utils_tests/test_html.py` — `test_urlize` (~line 250) and `test_urlize_unchanged_inputs` (~line 265); add escaped-entity regression here.
- `tests/template_tests/filter_tests/test_urlize.py`
- `tests/template_tests/filter_tests/test_urlizetrunc.py`

**Docs:** `docs/ref/templates/builtins.txt` (`urlize`/`urlizetrunc`) and `docs/ref/utils.txt` (`django.utils.html`).

**Ruled out:** `html.unescape('...&lt!')` behaves correctly (`<!`), and `smart_urlquote()` produces the correct quoted href. Direct imports failed only because `asgiref` is missing in the environment, unrelated to the bug.

**Conclusion:** Defect is in `urlize()`’s trailing-punctuation/entity boundary logic; it must not partially strip an HTML entity. Fix in `django/utils/html.py` around the `urlize` implementation and add a regression test in `tests/utils_tests/test_html.py`.
