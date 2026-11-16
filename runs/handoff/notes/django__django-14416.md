# Handoff: LocaleMiddleware redirects are cacheable without `Vary`

**Issue:** With `LocaleMiddleware` and a CDN/proxy cache, the language-prefix redirect is chosen from `Accept-Language`/`LANGUAGE_COOKIE_NAME`, but the redirect response carries no `Vary` header, so caches serve a stale redirect (wrong language).

**Files that matter**
- `django/middleware/locale.py`: `patch_vary_headers` is imported at line 6; `process_response` (lines 28–65) returns `self.response_redirect_class(language_url)` around lines 40–57 **without** patching `Vary`. The existing `patch_vary_headers(response, ('Accept-Language',))` at line 59 only reaches non-redirect responses. `process_request` (18–26) is not the culprit.
- `django/utils/translation/trans_real.py:518–556` (`get_language_from_request`): reads the cookie at 533 and `HTTP_ACCEPT_LANGUAGE` at 542, confirming both headers drive the redirect and both belong in `Vary`.

**Tests**
- `tests/i18n/patterns/tests.py`: `URLRedirectTests` (190–244), `URLVaryAcceptLanguageTests` (247–264), `PermanentRedirectLocaleMiddleWare` (15). Add the regression assertion to `URLRedirectTests`.
- Related: `tests/i18n/tests.py` `LocaleMiddlewareTests` (1744), `UnprefixedDefaultLanguageTests` (1762); `tests/cache/tests.py:1862` (`test_patch_vary_headers`).

**Docs:** `docs/topics/i18n/translation.txt` (LocaleMiddleware / language detection), `docs/topics/cache.txt` (`Vary`).

**Ruled out:** `patch_vary_headers` itself (`django/utils/cache.py:278`) works correctly; `Vary` handling in sessions/CSRF/gzip middleware; `process_request` language detection; prefixed-URL responses, which correctly omit `Vary` (line 59 guard).

**Conclusion:** Patch the redirect response in `process_response` with `patch_vary_headers(response, ('Accept-Language', 'Cookie'))` before returning it, and cover it in `URLRedirectTests`.
