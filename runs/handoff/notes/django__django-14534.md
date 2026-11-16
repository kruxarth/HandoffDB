# Handoff: `BoundWidget.id_for_label` ignores ChoiceWidget option IDs

**Issue:** For `CheckboxSelectMultiple` subwidgets, `BoundWidget.id_for_label()` recomputes `id_<name>_<index>` and ignores the `id` already set in `self.data['attrs']['id']` by `ChoiceWidget.options()`. This breaks custom `auto_id` formats.

**Key code:**
- `django/forms/boundfield.py:218-226` — `BoundField.id_for_label`; not the bug.
- `django/forms/boundfield.py:247`, `:279-280` — `BoundWidget.id_for_label`; it returns `'id_%s_%s' % (self.data['name'], self.data['index'])` instead of using `self.data['attrs']['id']`.
- `django/forms/widgets.py:551-580` — `ChoiceWidget` and `subwidgets()`.
- `django/forms/widgets.py:627` — `option_attrs['id'] = self.id_for_label(option_attrs['id'], index)`; this is where the desired option ID is produced.
- `django/forms/widgets.py:645`, `:765-773`, `:776` — `ChoiceWidget.id_for_label`, `RadioSelect.id_for_label`, `CheckboxSelectMultiple`.

**Tests:**
- `tests/forms_tests/tests/test_forms.py:684-723` — iterable boundfield IDs (`id_name_0`, `id_name_1`).
- `tests/forms_tests/tests/test_forms.py:3162-3203` — `BoundField.id_for_label` / custom widget ID tests.
- `tests/forms_tests/widget_tests/test_checkboxselectmultiple.py:198-208` — `test_label`; confirms group label has no `for` attribute.

**Docs:** No relevant docs were inspected or identified in this session; this is internal form-rendering behavior.

**Ruled out:** `BoundField.id_for_label` and `CheckboxSelectMultiple`/`RadioSelect.id_for_label` are not the cause. The group-label `for=""` behavior for `RadioSelect` is intentional. `auto_id=False` rendering is not the failing path.

**Conclusion:** Fix `BoundWidget.id_for_label()` to return the option ID from `self.data['attrs']['id']` when present, preserving a fallback for widgets without an ID. Add coverage for `CheckboxSelectMultiple` with a custom `auto_id` format.
