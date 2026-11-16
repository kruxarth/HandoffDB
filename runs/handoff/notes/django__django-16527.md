# Handoff: `show_save_as_new` missing add-permission check

## Issue
The admin "Save as new" button is shown to users who have change permission but not add permission. The flag only checks `save_as`, `change`, and `has_change_permission`, so the UI offers a create-style action to users who cannot add objects.

## Files and line ranges
- `django/contrib/admin/templatetags/admin_modify.py:70-106` — `submit_row()` builds the submit-row context. Lines 102-105 define `show_save_as_new`; add `and has_add_permission` to that condition chain. The sibling flag `show_save_and_add_another` (line 86) already gates on add permission, so this is the only gap.
- `django/contrib/admin/templates/admin/submit_line.html:5` — consumes `show_save_as_new` to render the `_saveasnew` submit input. No change needed; the fix is in the context builder.
- `django/contrib/admin/options.py:2244` — `_changeform_view()` detects `_saveasnew` in POST. Verify whether that branch re-checks `has_add_permission` server-side; the templatetag fix alone is presentation-only and should not be treated as the security boundary.

## Tests and docs
- `tests/admin_views/tests.py`, class `SaveAsNewTests` — add a regression case: user with change-but-not-add permission on the model must not see "Save as new" in the submit row.
- `tests/admin_views/tests.py` submit-row context assertions are the pattern to extend.
- `docs/ref/contrib/admin/index.rst` (`save_as` section) and the current release notes describe the behavior; update the release note if the change is backported.

## Ruled out
- `save_as` setting and `is_popup` — already gated in the same condition.
- `has_change_permission` — already present; not the missing piece.
- The `submit_line.html` template — correctly delegates to the flag.

## Conclusion
Add `has_add_permission` to `show_save_as_new` in `admin_modify.py:102`, mirroring the existing check on `show_save_and_add_another`.
