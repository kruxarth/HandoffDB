## Handoff: Cleanse session ID from error reports

**Issue:** Django error reports expose the session cookie, allowing session hijacking if reports are posted publicly. Session IDs should be filtered like other credentials (upstream PR #15352; see #29714).

**Relevant code:**
- `django/views/debug.py:105-222` — `SafeExceptionReporterFilter`. `hidden_settings` (112-114) matches API/TOKEN/KEY/SECRET/PASS/SIGNATURE, not `sessionid`; `cleanse_setting()` (116-140) filters settings only; `get_safe_request_meta()` (153-159) filters META keys but leaves `HTTP_COOKIE` intact; `get_post_parameters()` (184+) filters POST.
- `django/views/debug.py:379` — `c["request_COOKIES_items"] = self.request.COOKIES.items()` passes cookies to templates unfiltered. A `get_safe_cookies()`-style filter is needed.
- Templates: `django/views/templates/technical_500.html:418-435` renders COOKIES; `:440-452` renders META. `django/views/templates/technical_500.txt:51-55` renders COOKIES/META.

**Tests/docs:**
- `tests/view_tests/tests/test_debug.py`: `ExceptionReporterFilterTests` starts at 1401; `test_request_meta_filtering` at 1681; cleanse-setting tests at 1610-1737; cookie/request rendering coverage around 1019-1042 and 1188-1206; custom filter at 1700-1737.
- `docs/howto/error-reporting.txt:240-304` documents `SafeExceptionReporterFilter`, `cleansed_substitute`, and `hidden_settings`.
- `docs/ref/settings.txt:1343` documents `DEFAULT_EXCEPTION_REPORTER_FILTER`.

**Ruled out:** No existing references to the issue/PR in the tree; no existing cookie-specific safe accessor. META filtering alone is insufficient because `HTTP_COOKIE` does not match `hidden_settings`, and COOKIES is rendered directly.

**Conclusion:** Add cookie cleansing in `SafeExceptionReporterFilter` and use it for `request_COOKIES_items`; ensure both COOKIES and `HTTP_COOKIE` META hide the session cookie. Add regression tests for default/custom cookie names and update error-reporting docs.
