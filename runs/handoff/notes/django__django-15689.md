# Handoff: APPEND_SLASH adds latency to all slashless requests

## Issue
`CommonMiddleware` performs an extra URLconf lookup (`is_valid_path`) on **every** request whose path doesn't end in `/`, even successful ones. Introduced by commit `9390da7fb6e251eaa9a785692f987296cb14523f` (ticket #26293) in 1.9.5/1.10; previously the slash-append redirect was only computed for 404 responses.

## Files/lines that matter
- `django/middleware/common.py`
  - `process_request` (lines 34–61): line 53 calls `self.should_redirect_with_slash(request)` unconditionally — this is the performance regression.
  - `should_redirect_with_slash` (lines 63–68): performs `is_valid_path(request.path_info + "/")`, the expensive lookup.
  - `process_response` (line ~108): still contains the 404-based check `if response.status_code == 404 and self.should_redirect_with_slash(request)`. This is the mechanism that should remain (and is sufficient).
  - Docstring lines 19–26 already describes the old (correct) 404-based behavior.

## Tests/docs
- `tests/middleware/tests.py`, `CommonMiddlewareTest` (line 38+), especially `test_append_slash_have_slash` (42), `test_append_slash_slashless_resource` (51), `test_append_slash_slashless_unknown` (67), `test_append_slash_redirect` (76), `test_append_slash_redirect_querystring` (85). The redirect tests call `process_request` directly and will need to be rewritten to exercise `process_response`/the middleware callable.
- Docs: `docs/ref/settings.txt` (`APPEND_SLASH`) and `docs/ref/middleware.txt` (`CommonMiddleware`).

## Ruled out
PREPEND_WWW and the `BrokenLinkEmailsMiddleware` referer logic (line 164+) are unrelated to the cost; the regression is solely the `process_request` URLconf probe.

## Conclusion
Remove the `should_redirect_with_slash` call from `process_request` and rely solely on the 404 path in `process_response`, restoring pre-1.9.5 behavior while keeping tests and docs consistent.
