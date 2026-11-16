## Handoff: makemigrations requires SECRET_KEY

**Issue:** `makemigrations --check` fails with `ImproperlyConfigured: The SECRET_KEY setting must not be empty` when a project settings module omits `SECRET_KEY`. Referenced ticket #29324 attempted to fix this.

**Root cause:** `django/contrib/auth/tokens.py:18` — `PasswordResetTokenGenerator.__init__()` eagerly evaluates `self.secret = self.secret or settings.SECRET_KEY`. The module-level singleton `default_token_generator = PasswordResetTokenGenerator()` at line 97 runs at import time. `django/contrib/admin/apps.py` (`AdminConfig.ready()` → `autodiscover()`) imports auth forms/views, which pull in `django/contrib/auth/forms.py:11`, triggering the instantiation during command startup. The settings lookup happens in `django/conf/__init__.py:74-75`, which raises when `SECRET_KEY` is falsy.

**Files/lines that matter:**
- `django/contrib/auth/tokens.py:18` (eager read) and `:97` (import-time instantiation) — the fix site. Make `SECRET_KEY` access lazy, e.g. convert `secret` to a property deferring `settings.SECRET_KEY` until token generation/validation.
- `django/conf/__init__.py:74-75` — where the error originates; do not change.
- `django/core/checks/security/base.py:202-210` — `check_secret_key` already tolerates missing keys; not the cause (deployment checks only).
- `django/core/management/base.py` / `makemigrations.py` — inspected; no `SECRET_KEY` dependency found there.

**Tests:** `tests/auth_tests/test_tokens.py` is the natural regression location (existing `TokenGeneratorTest`, `MockedPasswordResetTokenGenerator`). Add a test that deletes `settings.SECRET_KEY` and asserts generator construction/import doesn't raise. `tests/check_framework/test_security.py:380-397` covers W009 behavior; `tests/migrations/test_commands.py` covers makemigrations generally.

**Ruled out:** management command infrastructure, migration writer/loader, sessions/messages/staticfiles backends, and the security check framework — none read `SECRET_KEY` at import or startup.

**Blocker:** `asgiref`, `sqlparse`, `pytz` are missing and PyPI is unreachable, so the repro could not be executed. Verification must be done in an environment with dependencies installed.

**Conclusion:** Fix `tokens.py` to lazily resolve `SECRET_KEY`, add the regression test, run `tests/auth_tests/test_tokens.py` plus `tests/admin_scripts`.
