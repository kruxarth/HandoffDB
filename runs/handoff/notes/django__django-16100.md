# Handoff: atomic handling for changelist `list_editable`

**Issue:** `changelist_view` can modify data through `list_editable`, but unlike change forms it is not wrapped in a transaction, so a failure can leave partial updates.

**Key code:**
- `django/contrib/admin/options.py`: `ModelAdmin.changelist_view` starts at line 1914 and lacks transaction handling. Compare `changeform_view` at line 2102, which wraps `_changeform_view` with `transaction.atomic(using=router.db_for_write(self.model))`; transaction import is at line 39. The fix should mirror this pattern around `changelist_view`.
- `django/contrib/admin/views/main.py`: `ChangeList.__init__` accepts/stores `list_editable` at lines 69 and 119-121. This is configuration/plumbing only, not the transaction site.

**Tests:** `tests/admin_changelist/tests.py` covers `list_editable` rendering around lines 337-399, multiuser edits around line 1008, and `_get_list_editable_queryset` around lines 1103-1149. Add a regression test that forces a `list_editable` save failure and verifies rollback/atomicity.

**Docs:** No docs were changed in this session. Relevant admin changelist/`list_editable` documentation is likely in `docs/ref/contrib/admin/index.txt`; verify before updating.

**Ruled out:** `views/main.py` `list_editable` handling is not where writes occur; `changeform_view` already has correct atomic behavior. Repository snapshot is Django 4.2 alpha.

**Conclusion:** The missing transaction is in `ModelAdmin.changelist_view`. Wrap it in `transaction.atomic(using=router.db_for_write(self.model))`, analogous to `changeform_view`, and add rollback coverage in `tests/admin_changelist/tests.py`.
