## Handoff: timesince() TypeError with USE_TZ and >1 month

**Issue:** `timesince()` crashes with `TypeError: can't subtract offset-naive and offset-aware datetimes` when `USE_TZ=True` and `d` is one month or more in the past.

**Root cause / relevant code:** In `django/utils/timesince.py`, the `timesince()` function starts at line 28. For intervals reaching the month/year path, it constructs a `pivot` `datetime.datetime(...)` around lines 93–100 without preserving `d.tzinfo`. That makes `pivot` naive while `now` is aware, causing the subtraction failure. `is_aware` is already imported at line 4.

**Fix conclusion:** When building the pivot, pass `tzinfo=d.tzinfo`, e.g. `datetime.datetime(..., tzinfo=d.tzinfo)`. This preserves awareness and allows the month/year calculation to subtract correctly.

**Tests:** Add/verify regression coverage in `tests/utils_tests/test_timesince.py`, specifically a `TimesinceTests` case like `test_long_interval_with_tz` using `@requires_tz_support`, `@override_settings(USE_TZ=True)`, `now = timezone.now()`, `d = now - datetime.timedelta(days=31)`, expecting `"1\xa0month"`.

**Docs:** Related documentation is in `docs/ref/utils.txt` for `timesince()` and `docs/ref/templates/builtins.txt` for the `timesince` template filter; no doc change appears necessary for this bug fix.

**Ruled out:** Shorter intervals do not hit the pivot path, so the bug only appears at month-or-greater intervals. The issue is not `timezone.now()` or `USE_TZ` generally, but the naive pivot construction in `timesince.py`.
