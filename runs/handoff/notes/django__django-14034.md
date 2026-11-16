# Handoff: MultiValueField ignores required subfield

**Issue:** An optional `MultiValueField` with `require_all_fields=False` and one required subfield accepts all-empty submitted values. With any non-empty sibling, validation fails as expected.

**Key code:** `django/forms/fields.py:966-1095` (`MultiValueField`). `__init__` at `988-997` stores `require_all_fields` and adjusts subfield `required` flags; `default_error_messages` at `983-986` defines `incomplete`. The bug is in `clean()` within this class: when the parent is optional and all submitted values are empty, it returns early through `compress([])`, skipping subfield validation.

**Tests:** `tests/forms_tests/tests/test_forms.py:3026` (`test_multivalue_optional_subfields`) is the closest regression location; `3072-3093` already covers `require_all_fields=False` optional cases; `2956` covers general multivalue validation. `tests/forms_tests/field_tests/test_multivaluefield.py:52` (`MultiValueFieldTest`) and `test_clean` at `64` cover field-level happy paths.

**Docs:** `docs/ref/forms/fields.txt`, `MultiValueField.require_all_fields` section, should be reviewed if behavior is clarified.

**Ruled out:** Widget/`MultiWidget` rendering, form-level required handling, and `require_all_fields=True` behavior. The failure is isolated to `MultiValueField.clean()`.

**Conclusion:** Confirmed bug. Fix `clean()` so required subfields are validated even when the parent is optional and all values are empty, instead of early-returning via `compress([])`. Add a regression test near `test_multivalue_optional_subfields` using two empty subfields where one is required.
