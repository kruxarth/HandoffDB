# Handoff: JSONField.bound_data crashes on None

## Issue
Rendering a bound form with no submitted value for an optional `JSONField` raises `TypeError: the JSON object must be str, bytes or bytearray, not NoneType`. Repro: `JSONForm({})` then `form.as_p()` with `JSONField(required=False)`.

## Key code
- `django/forms/fields.py:1251` — `JSONField.bound_data()` calls `json.loads(data)`. It only catches `json.JSONDecodeError`, so a `None` `data` raises an uncaught `TypeError`. This is the bug site.
- `django/forms/fields.py:1220` — `JSONField` class definition (subclass of `CharField`).
- `django/forms/boundfield.py:130` — where `bound_data(self.data, data)` is invoked during render; this is the call path that triggers the crash.
- `django/forms/fields.py:154` — base `Field.bound_data()`; `django/forms/fields.py:592` — `FileField.bound_data()`. Both inspected and ruled out: base returns `data` untouched; FileField already guards `None`/`FILE_INPUT_CONTRADICTION`.

## Ruled out
- `clean()` path is fine: `test_valid_empty` (`tests/forms_tests/field_tests/test_jsonfield.py:19-20`) already asserts `clean(None)` returns `None`. Only the render/bound_data path is broken.
- `prepare_value(None)` correctly returns `'null'` (`test_jsonfield.py:30`), so the issue is isolated to `bound_data`.

## Tests
- `tests/forms_tests/field_tests/test_jsonfield.py` (`JSONFieldTest`, `SimpleTestCase`). Add a regression test asserting a bound form with `None`/missing data renders without error (and `bound_data(None, ...)` returns `None`).

## Docs
- `docs/ref/forms/fields.txt` — `JSONField` section.
- `docs/releases/` (next release notes) — bugfix entry.

## Conclusion
Fix `JSONField.bound_data()` to short-circuit when `data is None` (return `None`), or otherwise guard before `json.loads`, matching PR #13844. The base/FileField implementations and the clean path need no change.
