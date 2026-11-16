# Handoff: URLValidator failures on Pythons patched for bpo-43882

## Issue
`URLValidator` accepts URLs that end in `\n` on Python builds carrying the bpo-43882 fix (3.10.0b1, 3.9 branch). Two subtests in `tests/validators/tests.py` fail with "ValidationError not raised":

- `'http://www.djangoproject.com/\n'`
- `'http://[::ffff:192.9.5.5]\n'`

Cause: the CPython fix makes `urllib.parse.urlsplit()` strip all `\n`, `\r`, and `\t` before splitting, so those characters never reach Django's component checks.

## Files that matter
- `django/core/validators.py`
  - Lines 1–13: imports, notably `urlsplit, urlunsplit` (line 5).
  - Line 65: `class URLValidator(RegexValidator)`; the relevant logic is its `__call__`, which does the length/regex checks and then re-parses via `urlsplit(value)` for the IPv6 netloc check. That re-parse is where the stripped newline is lost.
- `tests/validators/tests.py`
  - Lines 229–231: the two failing cases, under the comment "Trailing newlines not accepted".
  - Lines 221–234: surrounding `TEST_DATA` entries; `test_validators` (~line 320–330) runs them as subtests.

## Docs
- `docs/ref/validators.txt` (`URLValidator` section) — behavior contract for rejected input.
- `docs/releases/` — add a note if the fix is backported.

## Ruled out
- Not a regex bug: the regex never sees the newline.
- Not fixable by editing the tests to expect `None` — that would silently accept control characters, contradicting documented behavior and enabling header-injection-style input.
- Not related to `django/utils/ipv6.py` or the punycode/IDN fallback path.

## Conclusion
Reject unsafe characters before any parsing: add an `unsafe_chars = frozenset('\t\r\n')` class attribute to `URLValidator` and, at the top of `__call__` (after the type/length check), raise `ValidationError(self.message, code=self.code)` if `self.unsafe_chars.intersection(value)`. This restores deterministic behavior across Python versions and keeps existing tests unchanged.
