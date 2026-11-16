# Handoff: simplify `_check_fix_default_value()` in time fields

**Issue:** The three time-related `_check_fix_default_value()` implementations in `django/db/models/fields/__init__.py` can be simplified, and at least one has a bug: `timezone.now()` is called even when the result is not needed. Repo is Django 4.0 alpha (`django/__init__.py:3`).

**Relevant code (`django/db/models/fields/__init__.py`):**
- `1106-1136` — `DateTimeCheckMixin.check()` calls `_check_fix_default_value()` at 1112; base method at 1134.
- `1156-1189` — `DateField._check_fix_default_value()`; warning text/id `fields.W161` around 1184.
- `1296-1337` — `DateTimeField._check_fix_default_value()`; `fields.W161` at 1327.
- `2192-2230` — `TimeField._check_fix_default_value()`; calls `timezone.now()` at 2200, `fields.W161` at 2223.

Each method first checks `has_default()` but still computes `timezone.now()` unconditionally; the value is only needed on the warning path. `TimeField` additionally appears to compare a `datetime` from `timezone.now()` against a `time` default — reproduced: `datetime.datetime(...) <= datetime.time(...)` raises `TypeError`, so a `TimeField(default=time(...))` can crash the check.

**Tests:** `tests/invalid_models_tests/test_ordinary_fields.py` — `DateFieldTests.test_fix_default_value` (440) and `_tz` (474), `DateTimeFieldTests` (482, 516), `TimeFieldTests` (743-769). These assert the exact `fields.W161` messages, so warning text/ordering must stay unchanged.

**Ruled out:** `grep` shows no other callers of `_check_fix_default_value` or `fields.W161` outside this file and test module; no migration/backend code depends on it.

**Conclusion:** Refactor all three methods to early-return before calling `timezone.now()`, computing `now` only when a warning is emitted, and fix `TimeField` to compare against a `datetime.time` (or avoid the comparison) so valid time defaults don't raise `TypeError`. Update/verify the tests above.
