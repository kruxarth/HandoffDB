## Handoff note

**Issue:** Admin change forms show the “Hold down ‘Control’…” help text for `SelectMultiple` widgets even when `widget.allow_multiple_selected = False`.

**Relevant code**
- `django/contrib/admin/options.py:282-325` — `ModelAdmin.formfield_for_manytomany()` builds the form field.
- `django/contrib/admin/options.py:317-318` — the bug: it checks only `isinstance(form_field.widget, SelectMultiple)` and excludes `CheckboxSelectMultiple`/`AutocompleteSelectMultiple`, but does not check `form_field.widget.allow_multiple_selected`. It then injects the multi-select help text.
- `django/forms/widgets.py:805` — `SelectMultiple`; its render path already gates the `multiple` attribute on `allow_multiple_selected` (reported around lines 684-685), so widget rendering is correct.
- `django/forms/widgets.py:590` — `ChoiceWidget.allow_multiple_selected = False`.

**Tests/docs**
- `tests/admin_widgets/tests.py:66` — `AdminFormfieldForDBFieldTests`; `test_m2m_widgets` around lines 263-273 asserts the existing m2m help text. Add a regression case here with a `SelectMultiple` whose `allow_multiple_selected` is `False`.
- `tests/modeladmin/tests.py:746` — autocomplete widget exclusion coverage.
- Docs: `docs/ref/contrib/admin/index.rst` (`formfield_for_manytomany`, `filter_vertical`/`filter_horizontal`) and `docs/ref/forms/widgets.rst` (`SelectMultiple`/`allow_multiple_selected`).

**Ruled out**
- Widget rendering itself: `SelectMultiple` already respects `allow_multiple_selected`.
- `CheckboxSelectMultiple` and `AutocompleteSelectMultiple`: explicitly excluded.
- No relevant coverage found in `tests/admin_inlines/` or `tests/admin_views/`.

**Conclusion:** Fix the admin help-text condition in `django/contrib/admin/options.py:317-318` by also requiring `form_field.widget.allow_multiple_selected`. Add the regression test in `tests/admin_widgets/tests.py`.
