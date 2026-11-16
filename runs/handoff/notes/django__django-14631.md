## Handoff note

**Issue:** Refactor `BaseForm._clean_fields()` and `BaseForm.changed_data` to obtain values through `BoundField`, so `_clean_fields()` and `form[name].initial` stay consistent, and move per-field change detection into a `BoundField` method (e.g. `did_change()`).

**Relevant code**
- `django/forms/forms.py`
  - `full_clean()` lines 372–387; calls `_clean_fields()` at 385.
  - `_clean_fields()` starts line 389; currently iterates `self.fields.items()` and uses `get_initial_for_field()` / `_field_data_value()` directly rather than `BoundField`.
  - `has_changed()` line 435 delegates to `changed_data`.
  - `changed_data` starts line 438; this contains the per-field comparison logic that should move to `BoundField`.
  - `__iter__()` 146–148 and `__getitem__()` 150+ already yield/cache `BoundField` objects.
- `django/forms/boundfield.py`
  - `BoundField` class line 15; `__init__` line 17.
  - `data` property lines 116–121 wraps `_field_data_value()`.
  - `value()` lines 123–131 uses `initial` and `field.bound_data()`.
  - `initial` cached property lines 212–213.
  - Suitable location for `did_change()` and possibly `_bound_items`.

**Tests**
- `tests/forms_tests/tests/test_forms.py`
  - `test_changed_data` lines 2000–2025, including `ValidationError` behavior.
  - `test_datetime_clean_initial_callable_disabled` lines 2115+, which should be adjusted to cover the `_clean_fields()` / `BoundField.initial` mismatch.
  - `test_datetime_changed_data_callable_with_microseconds` lines 2125–2130.
  - Invalid-initial `changed_data` regression note at line 2953.

**Ruled out:** `_bound_items` does not exist anywhere under `django/forms/` (grep returned no output), so it must be added or replaced with existing `__iter__`/`__getitem__` access. No docs references were found requiring updates.

**Conclusion:** The issue is valid. Implement a `_bound_items` helper, add `BoundField.did_change()` based on `bf.data`/`bf.initial`, refactor `_clean_fields()` and `changed_data`, preserve disabled-field and `ValidationError` semantics, and extend the datetime test.
