## Handoff: contrib.messages CookieStorage crash on legacy cookies

**Issue:** After upgrading to Django 3.2, `CookieStorage` crashes when reading a `messages` cookie written by an older Django. The legacy cookie is raw JSON plus a timestamped signature (`[[...]]:1lTkj1:...`), not base64. `django/contrib/messages/storage/cookie.py:_decode()` (call at line 175) uses `self.signer.unsign_object(data, serializer=MessageSerializer)`. That reaches `django/core/signing.py:Signer.unsign_object()` (~line 195), which calls `b64_decode()` (~line 68) and raises `binascii.Error` before signature validation, so the existing `except signing.BadSignature` at `cookie.py:167` does not catch it.

**Mattering files/lines:**
- `django/contrib/messages/storage/cookie.py:157–178` — `_decode()` needs a legacy fallback.
- `django/core/signing.py:62–68, 178–196` — `unsign_object()`/`b64_decode()` behavior; not the root bug.
- `docs/releases/3.2.txt:738–740` — documents new RFC 6265 cookie format and old-format support until 4.1.

**Tests/docs:** `tests/messages_tests/test_cookie.py` (cookie encode/decode helpers and storage tests) and `tests/signing/tests.py` (sign/unsign object). Add a regression test for a legacy raw-JSON signed cookie. Release note candidate: `docs/releases/3.2.1.txt`.

**Ruled out:** Base64 padding in `signing.py` is not the root cause; the legacy cookie is not base64 at all. `BadSignature` handling alone is insufficient because `binascii.Error` escapes first. There is no `tests/signing_tests/` directory; signing tests live at `tests/signing/tests.py`.

**Conclusion:** Django 3.2 regression. `_decode()` must catch `signing.BadSignature`/`binascii.Error` and fall back to legacy decoding via `json.loads(self.signer.unsign(data), cls=MessageDecoder)` before returning empty messages.
