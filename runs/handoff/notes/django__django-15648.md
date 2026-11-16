# Handoff: Feed methods cannot be decorated

## Issue
`django.contrib.syndication.views.Feed` callables (e.g. `item_link`) break when wrapped by a decorator using `*args, **kwargs`, raising `TypeError: item_link() takes exactly 2 arguments (1 given)`. Root cause is the argument-count heuristic in `_get_dynamic_attr`.

## Key code
- `django/contrib/syndication/views.py:76-93` — `_get_dynamic_attr()`. Lines 82-88 hold the explanatory comment; line 89 is the bug: `if code.co_argcount == 2:` assumes `self` + one arg. A `functools.wraps`-decorated wrapper exposes only `*args/**kwargs`, so `co_argcount == 1` and it falls through to `attr()` with no argument.
- `django/contrib/syndication/views.py:56-63` — default `item_link()` (the common decorated target).
- `django/contrib/syndication/views.py:129-149` — all feed-level `_get_dynamic_attr` call sites sharing this logic.

## Tests
- `tests/syndication_tests/tests.py:593` — `test_item_link_error` (ImproperlyConfigured path).
- `tests/syndication_tests/feeds.py:8-40` (`TestRss2Feed`), `:173-177` (`item_link` override). No decorator coverage exists; grep for "decorat" in `tests/syndication_tests/` returns nothing.

## Docs
- `docs/ref/contrib/syndication.txt:245-262` — documents the "try `obj` arg, then no-arg, then class attribute" algorithm this code implements.
- `docs/ref/contrib/syndication.txt:105-125` — `item_*` single-`item` parameter contract.

## Ruled out
- No existing syndication tests or docs reference decorators.
- `django/utils/inspect.py` (`get_func_args`, signature-based helpers) exists but is unused by syndication; `inspect.signature` follows `__wrapped__`, so it is the natural replacement.
- No release note in `docs/releases/4.2.txt` (syndication section is a stub).
- Removing the `obj`/no-arg dual convention was considered per the report but is documented public behavior (lines 245-262), so not the fix.

## Conclusion
Replace the `co_argcount` check with signature inspection (e.g. `inspect.signature`/`django.utils.inspect`) that unwraps decorated callables, preserving both calling conventions. Add a decorated-`item_link` regression test in `tests/syndication_tests/`.
