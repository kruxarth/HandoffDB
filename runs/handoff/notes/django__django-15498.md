# Handoff: Empty `If-Modified-Since` header raises an exception

**Issue:** An empty-string `If-Modified-Since` request header used to be ignored but now raises an exception (500) since commit `d6aff369ad3`.

**Root cause:** `django/views/static.py`, `was_modified_since()` (lines 114–140), called from `serve()` at line 44 with `request.META.get("HTTP_IF_MODIFIED_SINCE")`. At line 129 the guard is `if header is None:`, so an empty string slips through. `re.match(...)` at line 131 returns `None`, and line 132 (`matches[1]`) raises `TypeError: 'NoneType' object is not subscriptable`. The `except (AttributeError, ValueError, OverflowError)` at line 138 does not catch `TypeError`, so the view crashes.

**Fix:** Change line 129 to `if not header:` (or add `TypeError` to the except tuple).

**Ruled out:** `django/utils/cache.py` `get_conditional_response()` lines 177–178 already short-circuits empty strings via `if_modified_since and parse_http_date_safe(...)`. `django/middleware/http.py` line 25 uses the same pattern. `django/utils/http.py` `parse_http_date()` (lines 104–121) raises `ValueError` for bad input, which `parse_http_date_safe()` (lines 145–150) converts to `None`; it never raises `TypeError`. The commit `d6aff369ad3` is absent from this snapshot repo (only `3fa43df`), so no diff was available.

**Tests:** Add a regression case to `tests/view_tests/tests/test_static.py` — `StaticTests` covers bogus headers at lines 82–107 (`test_is_modified_since`, `test_not_modified_since`), and `StaticUtilsTests.test_was_modified_since_fp` at line 187 is the unit-level analogue. `tests/conditional_processing/tests.py` covers the middleware path (invalid value at line 9/49) but does not exercise `was_modified_since`.

**Docs:** `docs/topics/conditional-view-processing.txt` and `docs/ref/middleware.txt` (line 141) describe conditional handling; no release note yet — add one under `docs/releases/4.1.txt`.
