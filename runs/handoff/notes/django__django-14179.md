# Handoff: DisallowedHost in `CsrfViewMiddleware._origin_verified()`

## Issue
`CsrfViewMiddleware._origin_verified()` calls `request.get_host()` without guarding against `DisallowedHost`. When a request carries a bad `Host` header plus an `Origin` header, the middleware raises `DisallowedHost` (a 400/500-ish error) instead of cleanly rejecting the request. The referer path in `process_view()` was already fixed for this in ticket #28693; the origin path was not.

## Files and lines
- `django/middleware/csrf.py`
  - L14: `DisallowedHost` already imported — no new import needed.
  - L229–231 (per the referenced commit): `_origin_verified()` — the unguarded `request.get_host()` call. This is the fix site.
  - L320–330: `process_view()` referer branch — the existing precedent. `good_referer = request.get_host()` is wrapped in `try/except DisallowedHost: pass`, leaving `good_referer = None` so matching proceeds against `CSRF_TRUSTED_ORIGINS` only. Mirror this pattern.

## Tests
- `tests/csrf_tests/tests.py` — add a case sending `HTTP_HOST` not in `ALLOWED_HOSTS` together with `HTTP_ORIGIN`, asserting a 403 with `REASON_BAD_ORIGIN` rather than a raised `DisallowedHost`.
- `tests/requests/tests.py` L652–810 — existing `get_host()`/`DisallowedHost` coverage; useful for host-header setup patterns.
- `tests/logging_tests/tests.py` L498 — how `DisallowedHost` logging is asserted.

## Docs
- `docs/ref/csrf.txt` (origin checking, `CSRF_TRUSTED_ORIGINS`) and `docs/ref/settings.txt` (`ALLOWED_HOSTS`).

## Ruled out
- The referer path (`process_view`, L320–330) already handles `DisallowedHost`; not the cause.
- Missing import — `DisallowedHost` is imported at L14.
- Cookie/token logic — unrelated to this failure.

## Conclusion
`_origin_verified()` must catch `DisallowedHost` around `request.get_host()` and treat the host as untrusted (return `False`), so the request is rejected with `REASON_BAD_ORIGIN` instead of propagating the exception.
