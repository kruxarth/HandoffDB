# Handoff note

Issue: `{% blocktranslate asvar %}` escapes interpolated variables, then stores the result as a plain `str`, so later `{{ var }}` escapes it again.

Key code:
- `django/templatetags/i18n.py:134-146` — `render_token_list()` builds `%(var)s` placeholders.
- `django/templatetags/i18n.py:148-201` — `BlockTranslateNode.render()`; `:180-185` `render_value()` calls `render_value_in_context()` (escaping); `:200-201` stores `result` as a plain string in context.
- `django/templatetags/i18n.py:84-101` — `TranslateNode.render()` already preserves `SafeData` with `mark_safe`, showing the expected asvar pattern.
- `django/template/base.py:1037-1050` — `render_value_in_context()` applies `conditional_escape`; `:1062-1070` — `VariableNode.render()` re-escapes non-safe values.

Tests/docs:
- `tests/template_tests/syntax_tests/i18n/test_blocktranslate.py:153-221` — existing escaping tests.
- Same file `:376-408` — asvar tests, but no double-escaping regression.
- `docs/topics/i18n/translation.txt:700-704` — documents the asvar example. Docs are not the bug.

Ruled out: `TranslateNode` asvar path handles safe strings correctly; the docs example is valid; the defect is specific to `BlockTranslateNode` storing escaped output as an unsafe `str`.

Conclusion: confirmed bug. The fix should preserve/mark the blocktranslate asvar result safe when autoescaping (rather than storing escaped content as plain `str`) before `context[self.asvar] = result`, and add a regression test using `"<>& Title"` asserting no `&amp;lt;`/double escaping.
