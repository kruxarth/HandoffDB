## Handoff note

**Issue:** `HttpResponse.set_cookie()` and `set_signed_cookie()` reject `datetime.timedelta` for `max_age`, raising `TypeError` from `int(max_age)`. `get_signed_cookie(max_age=timedelta(...))` already works because signing handles timedeltas.

**Relevant code**
- `django/http/response.py:210-252` — `set_cookie()`. `max_age` is stored at line 249 via `int(max_age)`, and used for `expires` at line 252. This is the failure point. The method already special-cases `expires` as `datetime.datetime` at lines 232-243, but not `max_age` as `datetime.timedelta`.
- `django/http/response.py:270+` — `set_signed_cookie()` forwards `**kwargs` to `set_cookie()`, so fixing `set_cookie()` should fix it too.
- `django/core/signing.py:265-279` — `TimestampSigner.unsign()` already converts `datetime.timedelta` to `total_seconds()` at lines 273-275. This explains why `get_signed_cookie()` works and rules out signing as the bug.

**Tests**
- `tests/responses/test_cookie.py` — existing `test_max_age_expiration()` and `test_max_age_int()` cover numeric `max_age`; add a timedelta case here.
- `tests/signed_cookies_tests/tests.py` — covers `set_signed_cookie()` behavior; add coverage confirming timedelta `max_age` works through signed cookies.

**Docs**
- `docs/ref/request-response.txt` documents `set_cookie()` / `set_signed_cookie()` arguments and should mention `max_age` accepts `datetime.timedelta`.

**Ruled out:** `TimestampSigner` / `get_signed_cookie()` already support timedeltas (`django/core/signing.py:273-275`); no signing change is needed. `set_signed_cookie()` is not independently broken.

**Conclusion:** Normalize `max_age` in `set_cookie()` when it is a `datetime.timedelta`, e.g. convert with `total_seconds()` before `int()`/`http_date()`. `set_signed_cookie()` will inherit the fix through its forwarded kwargs.
