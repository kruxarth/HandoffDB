## Handoff: admin.E002 does not reject FK attname in `raw_id_fields`

**Issue:** `raw_id_fields = ['author_id']` passes `admin.E002` because `Options.get_field()` resolves both field names and attnames, but the admin only validates that lookup succeeds. The field is then not honored as a raw-id field.

**Code:** `django/contrib/admin/checks.py`, `_check_raw_id_fields_item()` at lines 232–240. On successful `obj.model._meta.get_field(field_name)`, it returns no error. It should also verify `field.name == field_name`; if not, return `refer_to_missing_field(field=field_name, option=label, obj=obj, id='admin.E002')`. The caller `_check_raw_id_fields()` is lines 220–228.

**Tests/models:**
- `tests/modeladmin/test_checks.py`: `RawIdCheckTests` starts line 47; `test_missing_field` around line 59 covers nonexistent raw-id fields.
- `tests/admin_checks/tests.py`: `test_app_label_in_admin_checks` around lines 615–624 asserts the current `admin.E002` message for `raw_id_fields = ('nonexistent',)`.
- Relevant models: `tests/admin_checks/models.py` (`Album`, `Song`, `Author`, `Book`) and `tests/modeladmin/models.py` (`ValidationTestModel`, FK fields such as `band`).

**Docs:** `docs/ref/contrib/admin/checks.txt` documents `admin.E002`; wording should remain accurate after tightening the check.

**Ruled out:** The similar `_check_autocomplete_fields_item()` lookup pattern was not changed; this issue is specifically about `raw_id_fields` accepting attnames. No changes were made to `Options.get_field()` itself, since attname resolution is expected behavior elsewhere.

**Conclusion:** Fix is local to `_check_raw_id_fields_item()` by rejecting successful lookups where `field.name != field_name`, preserving `admin.E002`; add a regression test using an FK attname such as `author_id`/`band_id`.
