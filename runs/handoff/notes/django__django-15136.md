# Handoff: admin raw-ID inputs too small for UUID foreign keys

**Issue:** Admin raw-ID foreign-key inputs are too narrow to display UUID values (upstream PR #12926). No files were edited and no tests were run.

**Relevant code:**
- `django/contrib/admin/widgets.py:120-193` — `ForeignKeyRawIdWidget`; line 152 sets `class="vForeignKeyRawIdAdminField"`. This is where a `size` attribute should be derived from the related field.
- `django/contrib/admin/widgets.py:195+` — `ManyToManyRawIdWidget` subclasses it.
- `django/contrib/admin/widgets.py:358-360` — `AdminUUIDInputWidget` already uses `vUUIDField`.
- `django/contrib/admin/static/admin/css/forms.css:365-367` — `.vForeignKeyRawIdAdminField { width: 5em; }` is the direct cause of narrow rendering; contrast `.vTextField, .vUUIDField { width: 20em; }` at lines 353-355.
- `django/contrib/admin/options.py:219-235` and `:262` — widget instantiation in `formfield_for_foreignkey` / `formfield_for_manytomany`.
- `django/db/models/fields/__init__.py:2372-2380` — `UUIDField` forces `max_length=32`, useful for sizing.

**Tests/models:** `tests/admin_widgets/tests.py:534` (`ForeignKeyRawIdWidgetTest`, render expectations at 543-567), `:234` (`AdminForeignKeyRawIdWidget`), `:106-120`, `:441-446`. Fixtures: `tests/admin_widgets/models.py:26` (`Band.uuid`) and `Album.band` with `to_field='uuid'`.

**Docs:** `docs/releases/4.1.txt` has an admin section but no entry yet; `docs/releases/3.0.7.txt` only covers the unrelated XSS fix. Add a release note if behavior changes.

**Ruled out:** `RelatedObjectLookups.js` (no sizing logic), widget templates (`foreign_key_raw_id.html` has no `size`), `forms/widgets.py` `TextInput`, and `forms/fields.py:1201` `UUIDField`.

**Conclusion:** Fix by setting an appropriate `size` on `ForeignKeyRawIdWidget` (based on `rel.get_related_field().max_length`, e.g. 32/36) and/or widening `.vForeignKeyRawIdAdminField` in `forms.css`. Confirm whether `options.py` also needs a change; add a regression test rendering a UUID-backed raw-ID widget.
