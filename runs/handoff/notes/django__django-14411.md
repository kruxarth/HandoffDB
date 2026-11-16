## Handoff note

**Issue:** In admin/user forms, the `<label>` for `ReadOnlyPasswordHashWidget` includes a `for` attribute pointing to a non-labelable element. The widget renders text/`<div>` markup, not an input, so `for` must be omitted.

**Relevant code**
- `django/contrib/auth/forms.py:33-55` — `ReadOnlyPasswordHashWidget` and `ReadOnlyPasswordHashField.widget`; widget template is `auth/widgets/read_only_password_hash.html`, which renders no labelable control.
- `django/forms/boundfield.py:132-159` — `BoundField.label_tag()` adds `for` from `widget.id_for_label()` when an ID exists.
- `django/forms/widgets.py` — `Widget.id_for_label()` is the hook consulted by `BoundField.label_tag()`; override this in `ReadOnlyPasswordHashWidget` to return `''`.
- `django/contrib/admin/helpers.py:188-194` — `ReadOnlyAdminField.label_tag()` does not add `for`; line 215 only references the auth widget. Ruled out as the source.

**Tests/docs**
- `tests/auth_tests/test_forms.py:999-1030` — `ReadOnlyPasswordHashTest`, especially `test_render`; add regression assertion that rendered label has no `for`.
- `tests/auth_tests/test_views.py:1272` — notes widget use in admin user change view.
- `tests/admin_widgets/tests.py` and `tests/admin_widgets/models.py` — admin widget/readonly coverage.
- `docs/releases/1.11.1.txt:44` — historical widget-layout note only; no doc change needed.

**Ruled out:** Admin helper `label_tag` and the widget template as sources of `for`; the attribute comes from generic `BoundField.label_tag()`.

**Conclusion:** Add `id_for_label(self, id_): return ''` to `ReadOnlyPasswordHashWidget` so `BoundField.label_tag()` omits `for`, then add the regression test.
