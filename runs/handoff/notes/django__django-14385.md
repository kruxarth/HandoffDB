# Handoff: `simplify_regex` leaves regex metacharacters

**Issue:** `simplify_regex()` only strips `^`, `$`, and `?` after converting capture groups. Patterns such as `^\b(?P<slug>\w+)\B` produce `/\b<slug>\B` instead of `/<slug>`, and `\Ab/\Z` produces `/\Ab/\Z` instead of `/b/`.

**Key files/lines:**
- `django/contrib/admindocs/views.py:407-419` — `simplify_regex()`. It calls `replace_named_groups()` and `replace_unnamed_groups()` at 413-414, then does cleanup at line 416 with only `.replace('^', '').replace('$', '').replace('?', '')`. This line is the root cause: it leaves `\b`, `\B`, `\A`, and `\Z`.
- `django/contrib/admindocs/utils.py:141-142` — named/unnamed group matchers.
- `django/contrib/admindocs/utils.py:145-181` — `replace_named_groups()`.
- `django/contrib/admindocs/utils.py:183+` — `replace_unnamed_groups()`.

**Tests:** `tests/admin_docs/test_views.py:384-404`, especially `AdminDocViewFunctionsTests.test_simplify_regex` at 386-404. It currently covers anchors and capture groups but not `\b`, `\B`, `\A`, or `\Z`; add cases for the issue’s examples.

**Docs:** `docs/ref/contrib/admin/admindocs.txt` describes admindocs URL-pattern display; likely no doc change needed unless the cleanup behavior is documented.

**Ruled out:** The named/unnamed group replacement helpers are not responsible for dropping these tokens; they correctly handle capture groups. No other test file references `simplify_regex`, `replace_named_groups`, or `replace_unnamed_groups`.

**Conclusion:** Fix the cleanup step in `django/contrib/admindocs/views.py:416` to remove/translate the remaining regex metacharacters (`\b`, `\B`, `\A`, `\Z`), then extend `test_simplify_regex` with the reported patterns.
