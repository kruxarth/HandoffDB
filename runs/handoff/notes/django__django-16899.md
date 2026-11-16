## Handoff note

**Issue:** `ModelAdmin`’s `readonly_fields` check (`admin.E035`) reports only the list index, e.g. `"The value of 'readonly_fields[0]' is not a callable..."`, omitting the offending field name. Other checks (`list_editable`, `list_display`) include the name and should be mirrored.

**Key code:** `django/contrib/admin/checks.py`
- `_check_readonly_fields` / `_check_readonly_fields_item` (approx. lines 1119–1155; locate via `admin.E034`/`admin.E035`). This is where the E035 message is built.
- Compare `_check_list_display_item` at lines 893–918 (`admin.E108`) and `_check_list_editable_item` at lines 1094–1110 (`admin.E121`), which include both `label` and the field name.

**Tests:** `tests/admin_checks/tests.py`
- `test_nonexistent_field` lines 794–807 expects the current E035 string.
- `test_nonexistent_field_on_inline` lines 809–825 also expects E035; update both expected messages to include the field name.
- `tests/modeladmin/test_checks.py:520–531` covers the analogous `list_display` message, not `readonly_fields`.

**Docs:** Admin system-check documentation (`docs/ref/contrib/admin/checks.txt`, E034/E035 entries) should be checked/updated if it quotes the error text.

**Ruled out:** No separate `readonly_fields` validation path exists in `django/contrib/admin/helpers.py`; the check is centralized in `checks.py`. The grep found only the E035 tests above.

**Conclusion:** Modify the E035 `checks.Error` message in `_check_readonly_fields_item` to include the field name, e.g. `"The value of '%s' refers to '%s', which is not a callable, an attribute of '%s', or an attribute of '%s'."`, then update the two expected strings in `tests/admin_checks/tests.py`. No behavior change beyond messaging.
