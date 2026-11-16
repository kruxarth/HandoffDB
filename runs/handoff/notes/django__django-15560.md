# Handoff: `createsuperuser` and `UniqueConstraint` usernames

**Issue.** `createsuperuser` does not detect an existing `USERNAME_FIELD` when uniqueness is declared with `Meta.constraints = [UniqueConstraint(fields=[...])]` instead of `unique=True`. Duplicate input reaches the database and raises `IntegrityError`.

**Key code.**
- `django/contrib/auth/management/commands/createsuperuser.py`: `_validate_username()` (method following `handle()`, after L245) checks only `self.username_field.unique`. This is the bug: it ignores a single-field `UniqueConstraint` on `USERNAME_FIELD`. Relevant `handle()` call sites are L90, L136–137, L203–208, and L217; duplicate error text is at L245.
- `django/contrib/auth/checks.py:57` already handles this correctly by iterating `cls._meta.total_unique_constraints`; mirror that logic.
- `django/db/models/options.py:951` defines `total_unique_constraints`; `django/db/models/base.py:1208–1229` (`_get_unique_checks`) includes them, and `:1192` `validate_unique()` supports constraints.

**Tests/docs.** Add regression coverage in `tests/auth_tests/test_management.py`, class `CreatesuperuserManagementCommandTestCase` (starts L285); existing duplicate-username assertions are at L1062, L1073, and L1109. Add a custom user fixture with a single-field `UniqueConstraint` on `USERNAME_FIELD` in `tests/auth_tests/models/custom_user.py` or `invalid_models.py`. Related docs: `docs/ref/django-admin.txt` (`createsuperuser`) and `docs/topics/auth/customizing.txt` (custom users/`USERNAME_FIELD`).

**Ruled out.** Model-layer uniqueness: `Model.validate_unique()` / `_get_unique_checks()` already includes `total_unique_constraints`, and `auth.checks` supports `UniqueConstraint`. The command simply does not use model validation for username.

**Conclusion.** Patch `_validate_username()` to recognize a single-field `UniqueConstraint` covering `USERNAME_FIELD` and query via `get_by_natural_key()`; add the command regression test.
