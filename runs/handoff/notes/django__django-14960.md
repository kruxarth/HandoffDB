# Handoff: `createsuperuser` interactive `REQUIRED_FIELDS` validation

**Issue:** In interactive mode, `createsuperuser` skips validation for `REQUIRED_FIELDS` values supplied via command-line options. Raw strings reach `UserManager.create_superuser` instead of cleaned values (e.g. an FK PK). Non-interactive mode validates correctly.

**Key code:** `django/contrib/auth/management/commands/createsuperuser.py`
- Line 54 enumerates `REQUIRED_FIELDS`.
- Interactive `REQUIRED_FIELDS` loop, lines 124-129: accepts `options[field_name]` without calling `field.clean()`.
- `get_input_data()`, lines 208+: validates only prompted input, not option-provided values.
- Non-interactive validation path, around lines 181-199: already calls `field.clean()` and raises `CommandError`.

**Tests:** `tests/auth_tests/test_management.py`
- `test_fields_with_fk`, lines 450-467: non-interactive FK validation.
- `test_fields_with_fk_interactive`, lines 480-506: prompted interactive FK.
- `test_fields_with_fk_via_option_interactive`, lines 508-528: valid option-provided FK, but no invalid-value regression coverage.

**Docs:** `docs/ref/django-admin.txt` (`createsuperuser`) and `docs/topics/auth/customizing.txt` (`REQUIRED_FIELDS`, custom user models).

**Ruled out:** Non-interactive validation works; prompted interactive input works via `get_input_data()`; the issue is not in `create_superuser` or manager conversion. No separate `createsuperuser` test module exists; `auth_tests/test_management.py` is the relevant suite.

**Conclusion:** In the interactive branch, validate option-provided `REQUIRED_FIELDS` with `field.clean()` before assignment, mirroring the non-interactive `CommandError` behavior. Add a regression test for an invalid FK/option in `test_fields_with_fk_via_option_interactive`.
