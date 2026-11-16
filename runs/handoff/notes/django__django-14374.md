# Handoff: modernize `datetime.now()` / `utcnow()` usage

**Issue:** Django still calls `datetime.utcnow()`, `datetime.utcfromtimestamp()`, and `utctimetuple()`, which Python docs discourage. Replace with `datetime.now(timezone.utc)` and `datetime.fromtimestamp(ts, timezone.utc)`, and update docs examples for backporting.

**Code sites that matter**
- `django/utils/timezone.py:198-201` — `now()` uses `utcnow().replace(tzinfo=utc)`; central helper.
- `django/utils/feedgenerator.py:175-176` — `latest_post_date()` falls back to `utcnow()`.
- `django/utils/http.py:117,131` — `utcnow().year` and `utctimetuple()`.
- `django/utils/version.py:93` — `utcfromtimestamp()`.
- `django/core/files/storage.py:352` — `utcfromtimestamp()`.
- `django/core/cache/backends/db.py:127,239-241` — `utcfromtimestamp()`, `utcnow()`, naive `now()`.
- `django/contrib/sessions/backends/file.py:63-64` — `utcfromtimestamp()`.
- `django/http/response.py:207-208` — `expires.utcnow()`.
- `django/utils/dateformat.py:299`; `django/contrib/sitemaps/views.py:76`; `django/contrib/syndication/views.py:46`; `django/views/decorators/http.py:85` — `utctimetuple()`.

**Docs:** `docs/topics/i18n/timezones.txt:540` (`datetime.datetime.utcnow()` example) and `docs/ref/models/fields.txt:1665` (`datetime.date.utcnow()`).

**Tests to update:** `tests/utils_tests/test_http.py:291,297-300` mocks `datetime.utcnow`; `tests/responses/test_cookie.py:22,31`; `tests/utils_tests/test_feedgenerator.py:133-137`; `tests/utils_tests/test_dateformat.py:57-58`; `tests/migrations/test_writer.py:482-483,663-664`; `tests/foreign_object/tests.py:95`.

**Ruled out:** The pytz/`zoneinfo` migration (`django/utils/timezone.py:25-30`) and `USE_DEPRECATED_PYTZ` work are separate; no `zoneinfo` support is present in this snapshot. Formatting-only helpers `rfc2822_date`/`rfc3339_date` do not call `now()`.

**Conclusion:** No edits were made (tree clean). Apply the replacements above, preserving aware/naive behavior, then run the listed test modules and adjust mocks away from `utcnow`.
