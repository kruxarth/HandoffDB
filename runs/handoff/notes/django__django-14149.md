# Handoff: Validate the type of `ALLOWED_HOSTS`

## Issue
A string `ALLOWED_HOSTS` in `local_settings.py` silently passes Django's checks; iterating it matches each *character* against the `Host:` header. We need a system check that flags a non-list/tuple value (the issue suggests blacklisting strings, i.e. warn rather than hard-error).

## Where the code lives
- `django/core/checks/security/base.py`
  - Lines ~1–130: warning/error definitions, including `W020` (`"ALLOWED_HOSTS must not be empty in deployment."`, id `security.W020`, around line 99).
  - Lines ~130–260: the `@register(Tags.security, deploy=True)` check functions. `check_allowed_hosts` returns `[] if settings.ALLOWED_HOSTS else [W020]` (~line 219) — it only tests emptiness, never type. This is the function to extend, or to sit beside with a new check.
- `django/core/checks/registry.py` / `django/core/checks/__init__.py` if a new ID/tag is needed.

## Tests
- `tests/check_framework/test_security.py` — `CheckSecurityTest`-style tests; `test_allowed_hosts_empty` (~line 431) and `test_allowed_hosts_set` (~line 436) use `override_settings` and assert against `base.check_allowed_hosts(None)`. Add cases for a string value (e.g. `'example.com'`) and a non-list type there.

## Docs
- `docs/ref/checks.txt` line 504 — the `security.W020` entry; a new check ID needs an entry alongside it.
- `docs/ref/settings.txt` lines 59–95 — `ALLOWED_HOSTS` description; mention the new check if behavior changes.

## Ruled out
- `admin.E024` (`django/contrib/admin/checks.py:482`) and `models.E024` (`django/db/models/base.py:1539`) are unrelated checks with coincidentally matching IDs.
- `W020` cannot be reused for type validation: it is gated on emptiness and on `deploy=True`; a string is truthy so it never fires.

## Conclusion
The report is valid — no existing check inspects `ALLOWED_HOSTS`' type. Add a new security warning in `django/core/checks/security/base.py` (near `check_allowed_hosts`, ~line 219) that warns when the value is a `str`, register it with `Tags.security`, add tests in `tests/check_framework/test_security.py` and a doc entry in `docs/ref/checks.txt`.
