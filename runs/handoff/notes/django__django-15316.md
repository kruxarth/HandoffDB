# Handoff: `simplify_regex()` and non-capturing groups

**Issue:** `simplify_regex()` mishandles non-capturing groups `(?:...)`. For example, `^(?P<a>\w+)/b/(?:\w+)$` is rendered as `/<a>/b/<var>`, and `(?:foo)` becomes `<var>`, so non-capturing groups are treated as unnamed capturing groups.

**Key code:**
- `django/contrib/admindocs/views.py:407-417` — `simplify_regex()` is only a pipeline over helpers; the bug is not here.
- `django/contrib/admindocs/utils.py:142` — `unnamed_group_matcher = _lazy_re_compile(r'\(')` matches every `(`, including `(?:`. This is the root cause.
- `django/contrib/admindocs/utils.py:181-220` — `replace_named_groups()` / `replace_unnamed_groups()` rely on `_find_groups()` (174-179) and `_get_group_start_end()` (156-171); non-capturing groups are consumed and emitted as `<var>`.
- `django/contrib/admindocs/utils.py:145-153` — `replace_metacharacters()` runs afterward and may strip `?` from leftover `(?:` syntax if the matcher is changed.

**Tests/docs:**
- `tests/admin_docs/test_views.py:384` — `AdminDocViewFunctionsTests.test_simplify_regex`; add regression cases for `(?:...)`, alternation, nesting, and optional non-capturing groups.
- `tests/admin_docs/test_utils.py` — no direct tests for the `replace_*` helpers; consider adding coverage.
- `docs/topics/http/urls.txt:257,271` — mentions non-capturing groups, but not admindocs; no docs change appears necessary.

**Ruled out:** `simplify_regex()` itself and `django/utils/regex_helper.py` (its non-capturing support is unrelated). Full Django import/reproduction failed because `asgiref` is missing; helper behavior was exercised standalone.

**Conclusion:** Fix `unnamed_group_matcher` / `replace_unnamed_groups()` so `(?:...)` is not treated as an unnamed capturing group, then add regression tests. Confirm the intended output convention for non-capturing groups before editing.
