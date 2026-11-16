# Handoff: ISO-8601 whitespace before timezone offset in `parse_datetime`

## Issue
`django.utils.dateparse.parse_datetime()` returns `None` for valid ISO-8601 strings with whitespace between the time and timezone offset, e.g. `"2012-04-23T10:20:30.400 -02"`. ISO-8601 permits whitespace there. `"2012-04-23T10:20:30.400-02"` parses fine.

## Files and line ranges
- `django/utils/dateparse.py`: `datetime_re` at lines 22–27. Line 26, `r'(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$'`, lacks any whitespace allowance before the `tzinfo` group — this is the root cause. `date_re` (13–15) and `time_re` (17–20) are unaffected; `standard_duration_re` (29–38) is unrelated.
- Fix: allow whitespace (e.g. `\s*`) between the optional microseconds/seconds portion and the `tzinfo` group, keeping the existing timezone pattern intact.

## Tests
- `tests/utils_tests/test_dateparse.py`: `parse_datetime` valid-input cases at lines ~35–42 (including offset examples `...400-02`, `...400+02:30`, comma variant). Add cases with a space before `-02`/`+02:30`/`Z`. Invalid cases near lines 49–51 confirm `None` behavior is preserved for genuinely bad input.

## Docs
- `docs/ref/utils.txt` documents `parse_datetime` and the dateparse helpers; note that whitespace before the timezone offset is accepted.

## Ruled out
Replacing the regex with a `python-dateutil` dependency or inlining its ISO parser (issue's options 1 and 2) — too invasive for this repo; the existing regex approach is retained. No changes needed to `parse_date`, `parse_time`, or duration parsing.

## Conclusion
The bug is isolated to the `datetime_re` timezone boundary. Add optional whitespace before `tzinfo` in `django/utils/dateparse.py` line 26, cover it in `tests/utils_tests/test_dateparse.py`, and update `docs/ref/utils.txt`. This matches upstream PR #14368.
