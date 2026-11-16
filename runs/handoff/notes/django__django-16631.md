# Handoff: SECRET_KEY_FALLBACKS not honored for session auth hashes

## Issue
Rotating `SECRET_KEY` and moving the old value to `SECRET_KEY_FALLBACKS` logs out all users, contradicting the `SECRET_KEY_FALLBACKS` docs. Root cause: session auth hashes are derived only from the current `SECRET_KEY`, with no fallback check.

## Relevant code
- `django/contrib/auth/base_user.py:134-143` — `AbstractBaseUser.get_session_auth_hash()` calls `salted_hmac(key_salt, self.password, algorithm="sha256")` without `secret=`, so it always uses `settings.SECRET_KEY`.
- `django/contrib/auth/__init__.py:200-207` — `get_user()` compares the stored `session_hash` against only the single `user.get_session_auth_hash()`; mismatch flushes the session and returns anonymous.
- `django/utils/crypto.py` — `salted_hmac()` defaults `secret` to `settings.SECRET_KEY`; it has no fallback awareness.
- `django/core/signing.py:111-117` and `Signer.unsign` (~line 233) already pass/iterate `fallback_keys`, so *session payload* signing is fine.

## Related tests/docs
- Tests: `tests/check_framework/test_security.py:452-505` (W025 fallback checks); auth session tests under `tests/auth_tests/` (e.g. `test_auth_backends.py`, `test_basic.py`) and `tests/sessions_tests/`.
- Docs: `docs/ref/settings.txt` (`SECRET_KEY_FALLBACKS`) and `docs/topics/signing.txt`.

## Ruled out
Session cookie signing (`django/contrib/sessions/backends/base.py:92-113`, `signed_cookies.py`) and `Signer` already support fallbacks. `PasswordResetTokenGenerator` (`django/contrib/auth/tokens.py:22-38`) already implements `secret`/`secret_fallbacks`.

## Conclusion
Fix belongs in the auth hash: `get_session_auth_hash()` should accept a secret, and `get_user()` (and `update_session_auth_hash`) should verify against `SECRET_KEY` plus each `SECRET_KEY_FALLBACKS` entry, matching the `Signer.unsign` pattern.
