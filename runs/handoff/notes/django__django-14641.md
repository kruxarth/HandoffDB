# Handoff: Move `BoundField.initial()` time/datetime special-casing

## Issue
Follow-up to #32920. `BoundField.initial()` special-cases `datetime`/`time` values to strip microseconds according to `widget.supports_microseconds`. This should move into `BaseForm.get_initial_for_field()`, inside the `if callable(value)` block, with a possible later `Field`-level hook.

## Files and line ranges
- `django/forms/boundfield.py`: `BoundField.initial` cached property, roughly lines 229–240; issue cites lines 217–219 on `f5669fd`. Contains the `datetime`/`time` trimming logic. Remove it and drop the now-unused `import datetime` if applicable.
- `django/forms/forms.py`: `BaseForm.get_initial_for_field()`, roughly lines 481–500; callable branch at issue-cited lines 496–497. This is the target location. Add the datetime/time handling here.
- `tests/forms_tests/tests/test_forms.py`: `test_get_initial_for_field` around line 1985; `test_initial_datetime_values` around lines 2080–2160 covers callable datetime/time initial values and widget `supports_microseconds`. Update/extend these for form-level behavior.
- `tests/forms_tests/widget_tests/test_timeinput.py:18` and `test_datetimeinput.py:18`: display trimming tests; related but widget-level, not sufficient for this move.
- No `tests/forms_tests/tests/test_boundfield.py` exists; BoundField coverage lives in `test_forms.py`.

## Ruled out
A separate BoundField test module. Widget-only tests do not verify `get_initial_for_field()`.

## Conclusion
Move the special-case logic from `BoundField.initial()` to `BaseForm.get_initial_for_field()` under the callable branch, preserving behavior and existing tests; run `tests/forms_tests/`. No docs update identified as required.
