## Handoff note: formset deletion widget override

**Issue:** Add `deletion_widget` / `get_deletion_widget()` to formsets, mirroring `ordering_widget` / `get_ordering_widget()` (introduced for #29956), so the `DELETE` widget can be overridden.

**Code:** `django/forms/formsets.py`
- `:5` imports widgets; add `CheckboxInput` alongside `HiddenInput, NumberInput`.
- `:58` defines `ordering_widget = NumberInput`; add `deletion_widget = CheckboxInput` nearby.
- `:287-288` defines `get_ordering_widget()`; add analogous `get_deletion_widget()` returning `cls.deletion_widget`.
- `:411-417` uses `get_ordering_widget()` when building the `ORDER` field.
- `:419` is the `can_delete` branch where `DELETION_FIELD_NAME` / `DELETE` is added; use `widget=self.get_deletion_widget()` there, or assign the widget after field creation.

**Tests:** `tests/forms_tests/tests/test_formsets.py`
- Existing deletion tests: `:454-536`.
- Existing ordering-widget override test: `test_formsets_with_order_custom_widget`, `:605-628`; add an analogous deletion-widget test covering both class attribute and method override.
- Combined ordering/deletion coverage: `:679`.

**Docs:**
- `docs/topics/forms/formsets.txt:530-563` documents `ordering_widget` and `get_ordering_widget()`; add matching `deletion_widget` / `get_deletion_widget()` docs.
- Release-note precedent: `docs/releases/3.0.txt:215-216`; add the equivalent note to the current release notes.

**Ruled out:** No new widget class is needed. `CheckboxInput` already exists at `django/forms/widgets.py:512`. No changes to `_should_delete_form()`, validation, `can_delete`, or `formset_factory()` behavior.

**Conclusion:** Implement the feature by copying the existing ordering-widget pattern, defaulting to `CheckboxInput`, and add tests/docs.
