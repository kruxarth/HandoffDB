## Handoff

**Issue:** `createsuperuser` fails in non-interactive mode when `REQUIRED_FIELDS` contains a `ForeignKey` or `ManyToManyField`. The command validates the raw value with `field.clean(value, None)` and then passes it to `create_superuser()`. For `ForeignKey`, `clean()` returns an integer PK while `create_superuser()` expects a model instance; passing an instance instead makes `ForeignKey.to_python()` reject it. M2M values are lists of PKs and also fail validation.

**Key files/lines:**
- `django/contrib/auth/management/commands/createsuperuser.py:181` — non-interactive `REQUIRED_FIELDS` loop containing the problematic `field.clean()` call. Lines `54` and `124` are other `REQUIRED_FIELDS` loops; `_get_input_message()` at `220-231` already handles related/M2M display.
- `django/db/models/fields/related.py:917-936` (`ForeignKey.to_python()`), `:938` (`validate()`), `:1149` (`ManyToManyField`).
- `django/db/models/fields/__init__.py:664` (`Field.clean()`), `:1763+` (`IntegerField` conversion). These explain the conversion behavior; they are not the fix location.

**Tests/docs:**
- `tests/auth_tests/test_management.py:253` `CreatesuperuserManagementCommandTestCase`; M2M tests at `509`, `526`, `551`, `581`; non-interactive tests at `728`, `844`, `989`.
- `tests/auth_tests/models/with_foreign_key.py` (`CustomUserWithFK`) and `with_many_to_many.py` (`CustomUserWithM2M`, `CustomUserWithM2MThrough`).
- `docs/ref/django-admin.txt:1660-1730`; `docs/topics/auth/customizing.txt:569-592`.

**Ruled out:** Changing `ForeignKey.to_python()` or `Field.clean()` generally; the defect is command-side handling of non-interactive `REQUIRED_FIELDS`.

**Conclusion:** Fix belongs in `createsuperuser`, special-casing `field.many_to_many` and related-field PK conversion before calling `create_superuser()`. Add regression coverage in `tests/auth_tests/test_management.py`. No code changes were made; working tree is clean.
