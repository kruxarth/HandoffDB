# Handoff: ModelAdmin radio_fields overrides empty_label

## Issue
When `ModelAdmin.radio_fields` includes a `ForeignKey`, `ModelAdmin.formfield_for_foreignkey()` overwrites a caller-supplied `empty_label`, so custom labels from a subclassed `formfield_for_foreignkey()` are ignored.

## Relevant code
- `django/contrib/admin/options.py`
  - `formfield_for_foreignkey()` lines 251–279.
  - Line 272 is the bug: `kwargs["empty_label"] = _("None") if db_field.blank else None`.
  - The radio widget setup is lines 266–270, which is why this path is taken when `radio_fields` is set.
  - `formfield_for_manytomany()` lines 281+ was inspected but is not implicated in this ForeignKey-specific report.
  - `formfield_for_choice_field()` lines 222–230 was ruled out: it handles choices, not FK `empty_label`.

## Tests and docs
- `tests/admin_widgets/tests.py`
  - `test_radio_fields_ForeignKey` lines 135–142 asserts `ff.empty_label is None`.
  - `test_choices_with_radio_fields` lines 234–239 covers choice-field radio rendering.
- `tests/admin_widgets/widgetadmin.py` lines 31–35 contains an example `formfield_for_foreignkey()` override.
- Relevant docs: `docs/ref/contrib/admin/index.txt` sections for `ModelAdmin.radio_fields` and `formfield_for_foreignkey()`.

## Ruled out
The many-to-many formfield path and choice-field radio path do not cause this behavior. Existing tests cover radio widget selection but not preservation of a custom FK `empty_label`.

## Conclusion
Fix line 272 to preserve an existing value, e.g.:
`kwargs["empty_label"] = (kwargs.get("empty_label") or _("None")) if db_field.blank else None`

Add a regression test in `tests/admin_widgets/tests.py` near `test_radio_fields_ForeignKey` using a `formfield_for_foreignkey()` override that sets `empty_label`, with `radio_fields` configured, and assert the custom label survives.
