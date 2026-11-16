# Handoff: DurationField.clean crashes on malformed ISO-8601 input

## Issue
`DurationField.clean('P3(3D')` raises an uncaught `ValueError: could not convert string to float: '3(3'` instead of a `ValidationError`.

## Root cause & files
- `django/utils/dateparse.py`, `iso8601_duration_re` (~lines 40-50): the `.` characters in the regex are **unescaped**, so they match any character. `'P3(3D'` therefore matches as an ISO duration with `days='3(3'`.
- `django/utils/dateparse.py`, `parse_duration` (~lines 140-160): line 154's dict comprehension `{k: float(v) ...}` then crashes on `'3(3'`. The regex must be tightened (escape `.`/restrict to digits) so this input fails to match and `parse_duration` returns `None`.
- `django/forms/fields.py`, `DurationField.to_python` (~lines 482-509): only catches `OverflowError`; it relies on `parse_duration` returning `None` for bad input. No change needed here once the regex is fixed.
- `standard_duration_re` (lines 29-38) is anchored and character-classed correctly — not the culprit.

## Tests
- `tests/utils_tests/test_dateparse.py`, `DurationParseTests` (line 64+): add cases asserting `parse_duration('P3(3D')` (and similar `P...` junk) returns `None`.
- `tests/forms_tests/field_tests/test_durationfield.py`, `DurationFieldTest.test_durationfield_clean` (line 14+): add `f.clean('P3(3D')` raising `ValidationError` "Enter a valid duration."

## Docs
None directly; behavior matches documented `DurationField` validation.

## Ruled out
- `DurationField.to_python` logic (correct except it can't catch `ValueError` raised downstream).
- `standard_duration_re` / non-ISO formats.

## Conclusion
Fix the unescaped `.` in `iso8601_duration_re` in `django/utils/dateparse.py`; add regression tests in both test files above.
