# Handoff: UserAdmin password-reset link broken when accessed via `to_field`

**Issue.** When the UserAdmin change view is reached through a relation with `to_field` (e.g. `to_field="uuid"`), the URL becomes `/user/<uuid>/change/?_to_field=uuid`. `UserChangeForm` hardcodes the password help-text link as `"../password/"`, which resolves to `/user/password/` instead of `/user/<pk>/password/` → 404.

**Key code.**
- `django/contrib/auth/forms.py` — `UserChangeForm.__init__` (~lines 120–150): `password.help_text = password.help_text.format("../password/")`. Fix: `f"../../{self.instance.pk}/password/"`. The `ReadOnlyPasswordHashField` definition with the `"this form"` help text is immediately above.
- `django/contrib/admin/options.py` — `TO_FIELD_VAR` (line 71), `to_field_allowed()` (~line 492), and changeform `_to_field` handling (~lines 1297, 1344–1346). These explain the `?_to_field=` query string but are not the bug.

**Tests.**
- `tests/auth_tests/test_forms.py` — `UserChangeFormTest` (line 813) is where to assert the generated help-text URL.
- `tests/auth_tests/test_views.py` — `ChangelistTests.test_user_change_password` (line 1445) inspects the link; `UUIDUserTests` (line 1546) provides UUID users; `test_password_change_bad_url` (line 1490) and `test_user_change_password_passes_user_to_has_change_permission` (line 1498) confirm the password view still routes by pk.
- `tests/auth_tests/models/with_foreign_key.py` (line 20) shows an existing `to_field` relation.

**Ruled out.** `to_field_allowed` already permits non-pk targets; admin URL/filter preservation works correctly. The defect is solely the hardcoded relative path in the help text.

**Conclusion.** Build the link from `self.instance.pk` (`../../<pk>/password/`) so it is correct under `_to_field`, and add a regression test covering the UUID/`to_field` change-view case.
