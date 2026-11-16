# Handoff: conditional `ModelAdmin.get_inlines()` breaks on change

## Issue
`ParentAdmin.get_inlines()` returns `ChildInline` only when `obj.show_inlines` is true. Toggling the flag off works, but toggling it on (False → True) and saving raises "ManagementForm data is missing... child_set-TOTAL_FORMS, child_set-INITIAL_FORMS". The inline was never rendered in the GET response, so the POST carries no inline fields, yet a formset is built for it during POST.

## Files and line ranges
- `django/contrib/admin/options.py:338` — `ModelAdmin.get_inlines()`.
- `django/contrib/admin/options.py:602-615` — `get_inline_instances()`, just iterates `get_inlines()`.
- `django/contrib/admin/options.py:801-806` — `get_formsets_with_inlines()`.
- `django/contrib/admin/options.py:1493-1516` — `get_inline_formsets()` (zips instances with formsets).
- `django/contrib/admin/options.py:1551-1630` — `_changeform_view()`. **This is the bug site**: after `form.is_valid()`/`save_form()`, formsets are created from `new_object` (the instance already carrying `show_inlines=True`), so the inline is instantiated against POST data that never contained its management form.

## Tests
- `tests/admin_inlines/tests.py` (`TestInline`, `TestInlineAdminForm`) — natural home for a regression test.
- `tests/admin_inlines/admin.py` / `models.py` — inline fixtures; add a boolean-flag parent here.
- `tests/generic_inline_admin/tests.py:407-460` — `get_formsets_with_inlines` / `get_inlines` override tests.
- `tests/admin_views/tests.py:6513+` — `GetFormsetsWithInlinesArgumentTest` (obj is None on add, set on change).

## Docs
- `docs/ref/contrib/admin/index.txt:1655-1680` — `get_inline_instances` / `get_inlines` reference.
- `docs/releases/3.0.txt:110` — `get_inlines` introduction.

## Ruled out
`get_inlines`/`get_inline_instances`/`get_formsets_with_inlines` are not at fault; they correctly reflect `obj`. `ManagementForm` validation in `django/forms/formsets.py:60` is correct — the formset genuinely was never rendered.

## Conclusion
`_changeform_view` must build formsets/inline instances from the pre-validation instance (`form.instance` before `is_valid()`, i.e. the loaded `obj`) rather than the post-`save_form` `new_object`; otherwise inlines enabled by the very change being submitted appear out of nowhere and fail management-form validation.
