# Handoff: IndexError for takes_context tags with no parameters

## Issue
A `simple_tag`/`inclusion_tag` declared with `takes_context=True` but omitting the required `context` argument raises an opaque `IndexError` instead of the intended `TemplateSyntaxError` when the tag also takes no other arguments (empty `params` list).

## Root cause and files
- `django/template/library.py`, `parse_bits()` — the `takes_context` validation around line 246 does `if params[0] == 'context':` before checking that `params` is non-empty. With zero parameters this indexes an empty list. The existing `else` branch (raising `TemplateSyntaxError` with the message `"'%s' is decorated with takes_context=True so it must have a first argument of 'context'"`) is never reached.
- Fix belongs here: guard for empty `params` (e.g. `if params and params[0] == 'context':`) so the same informative `TemplateSyntaxError` is raised.

## Tests
- `tests/template_tests/test_custom.py`
  - `test_simple_tag_missing_context` (lines ~163-168)
  - `test_include_tag_missing_context` (lines ~250-255)
  - Both currently only cover the case where another parameter exists; add no-parameter variants asserting `TemplateSyntaxError` with the same message.
- Fixtures: `tests/template_tests/templatetags/custom.py` and `tests/template_tests/templatetags/inclusion.py` — add tags mirroring the issue (e.g. `simple_tag_no_params_without_context_parameter`).

## Docs
- `docs/howto/custom-template-tags.txt` — "Simple tags" / `takes_context` section documents the requirement; no doc change needed, but relevant for wording of the error.

## Ruled out
- The `takes_context` check itself works correctly when at least one parameter is supplied (existing tests pass); failure is purely the empty-list indexing.
- `TagHelperNode`/`InclusionNode` rendering is unaffected; error occurs at compile time.

## Conclusion
One-line guard in `parse_bits` plus regression tests for simple and inclusion tags with no parameters.
