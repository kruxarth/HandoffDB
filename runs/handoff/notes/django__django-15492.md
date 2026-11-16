# Handoff: `RemoteUserBackend.synchronize_user`

**Issue:** Add a `synchronize_user(request, user)` hook to `RemoteUserBackend` so custom backends can sync remote attributes into Django users on every authentication. It complements `configure_user()`, which only runs when a user is newly created.

**Key code:** `django/contrib/auth/backends.py` — `RemoteUserBackend` class near the end of the file (~lines 197–235). `authenticate()` (~lines 203–220) currently fetches/creates the user and calls `configure_user()` only when `created` is true. Add `synchronize_user()` with the same signature as `configure_user()` (~lines 228–230), and call it for every non-`None` user after fetch/create and before returning. `configure_user()` cannot be reused because it is creation-only.

**Tests:** `tests/auth_tests/test_remote_user.py` — `CustomRemoteUserBackend` (line 207), its `configure_user()` override (line 218), and `CustomRemoteUserBackendTest` (line 229) are the patterns to extend. Add coverage that `synchronize_user()` runs for existing users, newly created users, and when `create_unknown_user = False` but a user is found. Related classes: `RemoteUserNoCreateBackend` (line 175), `AllowAllUsersRemoteUserBackendTest` (line 196).

**Docs:** `docs/ref/contrib/auth.txt` — `RemoteUserBackend` method documentation around line 615, especially `configure_user` (~line 650); add `synchronize_user(request, user)`. `docs/howto/auth-remote-user.txt` also relates.

**Ruled out:** No changes to `RemoteUserMiddleware` and no new setting; the hook belongs solely on the backend. Reusing `configure_user()` for synchronization is insufficient.

**Conclusion:** Implement `synchronize_user()` on `RemoteUserBackend`, call it unconditionally after user retrieval/creation in `authenticate()`, document it, and add tests. Context: Django 4.1 alpha.
