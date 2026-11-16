# Handoff: Trunc()/Extract() tzinfo sign reversal

## Issue
`Etc/GMT-10` (UTC+10) produces `AT TIME ZONE 'Etc/GMT+10'` (UTC−10) in Django 3.2; 3.1 produced `-10`. Cause: `django/utils/timezone.py:74-76` `_get_timezone_name()` now returns `str(timezone)` (`"Etc/GMT-10"`) instead of `"+10"`. `TimezoneMixin.get_tzname()` (`django/db/models/functions/datetime.py:17-28`, call at :27) passes that name to the backends, whose `_prepare_tzname_delta()` blindly swaps every `+`/`-`, corrupting IANA zone names.

## Files and lines
- `django/db/backends/postgresql/operations.py:46-51` `_prepare_tzname_delta`, used by `_convert_field_to_tz` (:53-56); all trunc/extract SQL :41-76.
- `django/db/backends/mysql/operations.py:78-...` same method, caller :90.
- `django/db/backends/oracle/operations.py:110-...` same method, caller :129.

Fix: only flip signs for offset-style names (`+0500`/`-0500`); leave names like `Etc/GMT-10` untouched.

## Tests and docs
`tests/db_functions/datetime/test_extract_trunc.py` — `ZONE_CONSTRUCTORS` :32-34, `DateFunctionWithTimeZoneTests` :1141+, especially `test_extract_func_with_timezone` :1143-1235; add an `Etc/GMT-10` subTest there. Docs: `docs/ref/models/database-functions.txt` (`tzinfo` on Trunc/Extract).

## Ruled out
Not pytz-specific: zoneinfo gives `str()` = `Etc/GMT-10` but `tzname()` = `+10`. The 3.2 `_get_timezone_name()` change is intentional (cache keys, template context) — do not revert it.

## Conclusion
The bug is the backend sign-flipping helper; fix all three backends. Tests could not be executed here because pytz is missing from the repo interpreter.
