## Handoff: Deprecate `CryptPasswordHasher`

**Issue:** Deprecate `CryptPasswordHasher` in Django 4.1 and remove it in Django 5.0. Rationale: legacy UNIX-only support, nearly undocumented, and Python’s `crypt` module is deprecated in 3.11.

**Code:** `django/contrib/auth/hashers.py`
- `CryptPasswordHasher` begins at line 799 (class block shown around 790–850); it subclasses `BasePasswordHasher` and currently emits no deprecation warning.
- `warnings` is already imported at line 7, but `RemovedInDjango50Warning` is not imported in this file.
- Existing warning at line 283 is unrelated (`BasePasswordHasher.harden_runtime()`).
- Add the deprecation warning in `CryptPasswordHasher.__init__` and import `RemovedInDjango50Warning` from `django.utils.deprecation`.

**Tests:** `tests/auth_tests/test_hashers.py`
- `CryptPasswordHasher` is referenced at lines 206, 224, and 234.
- Add/update tests to assert the deprecation warning when instantiating/using the hasher.

**Docs:**
- `docs/releases/4.1.txt`: add a note under “Features deprecated in 4.1” (section starts line 554).
- `docs/topics/auth/passwords.txt:442`: included-hashers list still names `CryptPasswordHasher`.
- `docs/releases/1.10.txt:686`: historical release note; leave unchanged.

**Ruled out:** The `django.utils.crypto` import at `hashers.py:13` is unrelated. There is no top-level `crypt` import in `hashers.py`; Python’s `crypt` deprecation is motivation, not a direct import failure. No existing `RemovedInDjango50Warning` usage exists in `hashers.py`.

**Conclusion:** Deprecate, do not remove, in 4.1. Add `RemovedInDjango50Warning`, update tests and 4.1 release notes; removal belongs to Django 5.0.
