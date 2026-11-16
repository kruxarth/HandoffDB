## Handoff note: malformed Referer crashes CSRF middleware

**Issue:** `CsrfViewMiddleware` calls `urlparse()` on `HTTP_REFERER` without handling `ValueError`. A Referer such as `https://[` raises an uncaught exception instead of being rejected as malformed.

**Key code:** `django/middleware/csrf.py`
- Line 11 imports `urlparse`.
- Lines 25–31 define CSRF rejection messages, including `REASON_MALFORMED_REFERER`.
- Around line 244, inside `_check_referer()`, `referer = urlparse(referer)` is unguarded. This is the defect: wrap it in `try/except ValueError` and raise `RejectRequest(REASON_MALFORMED_REFERER)`.
- Existing validation after parsing rejects empty scheme/netloc and insecure schemes, but never runs for unparseable input.

**Tests:** `tests/csrf_tests/tests.py`
- `test_https_malformed_referer` at lines 321–356 covers empty, non-ASCII, protocol-relative, and `https://` Referers, but not `https://[`.
- `test_https_malformed_host` at lines 306–318 exercises malformed `HTTP_HOST`, not malformed Referer.
- Add a regression case setting `HTTP_REFERER = "https://["` and asserting the 403 malformed-Referer response.

**Docs:** `docs/ref/csrf.txt` and `docs/howto/csrf.txt` describe Referer checks/trusted origins; no behavioral doc change appears necessary, but confirm the malformed-Referer rejection remains documented consistently.

**Ruled out:** Host validation, Origin checking, and existing malformed-Referer branches are not the cause; the failure occurs earlier, during `urlparse()` itself. Existing tests pass because they do not include a syntactically invalid bracketed URL.

**Conclusion:** Fix `_check_referer()` by catching `ValueError` from `urlparse()` and rejecting with `REASON_MALFORMED_REFERER`; add the `https://[` regression test.
