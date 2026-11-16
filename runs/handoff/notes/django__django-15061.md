# Handoff: Remove `for=...` from MultiWidget labels

**Issue:** `MultiWidget.id_for_label()` appends `_0` to the field ID, so labels for MultiWidget-backed fields render `<label for="id_field_0">` — an arbitrary index the widget user can't control. Proposal: drop the override entirely so MultiWidget inherits the base `Widget.id_for_label()` (or returns `None`), producing a label with no `for`.

**Key code:**
- `django/forms/widgets.py:851-856` — `MultiWidget.id_for_label()`, returns `id_ + '_0'`. This is the method to remove/change.
- `django/forms/widgets.py:268-279` — base `Widget.id_for_label()` (returns `id_`), which MultiWidget would inherit.
- `django/forms/widgets.py:645` (RadioSelect, `index='0'`) and `765-773` (ChoiceWidget) — separate, indexed label logic; untouched.
- `django/forms/boundfield.py:165-175` — `label_tag()`; already guards with `if id_for_label:`, so a `None` return simply omits `for=`. Also `boundfield.py:219-227` (`BoundField.id_for_label`) and `:290`.
- `django/contrib/admin/widgets.py:307-308` — AdminRadioSelect delegates to its inner widget; unaffected.

**Tests asserting the `_0` suffix (must change):**
- `tests/forms_tests/field_tests/test_multivaluefield.py:144,167` (`<label for="id_field1_0">`).
- `tests/postgres_tests/test_ranges.py:668,703,720,757` (SplitDateTimeRangeField wraps MultiWidget).

**Ruled out:** `SplitArrayWidget` (`django/contrib/postgres/forms/array.py:125-130`) and its test `tests/postgres_tests/test_array.py:1111` define their own `id_for_label`, not inherited from MultiWidget — unaffected. RadioSelect/CheckboxSelectMultiple label tests (`test_radioselect.py:33-42`, `test_checkboxselectmultiple.py:186-187`) are independent. `test_multiwidget.py` never asserts a label `for`. BoundField tests `test_forms.py:2996,3020,3026` cover overrides, not MultiWidget.

**Docs:** `docs/ref/forms/widgets.txt:277-284` (`id_for_label` contract) and the MultiWidget section `:339-422`; add a release note under "Features deprecated in 4.1" in `docs/releases/4.1.txt:260-273` if deprecating rather than removing outright.

**Conclusion:** Delete `MultiWidget.id_for_label` so labels for MultiWidget fields carry no `for` attribute; update the four test files' expected HTML and add the release note.
