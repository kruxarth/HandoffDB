## Handoff note

**Issue:** Management command help text collapses newlines (`help` output flattens multi-line text). Root cause is not `HelpFormatter` itself but that `BaseCommand.create_parser()` hardcodes Django’s formatter, preventing commands from selecting a formatter such as `RawTextHelpFormatter`.

**Key code:**
- `django/core/management/base.py:105` — `DjangoHelpFormatter(HelpFormatter)`. It reorders actions for help output but inherits default whitespace-collapsing behavior.
- `django/core/management/base.py:284-296` — `BaseCommand.create_parser()`. Line 292 hardcodes `formatter_class=DjangoHelpFormatter` when constructing `CommandParser`, so callers cannot override it via `**kwargs`.
- `django/core/management/base.py:46-66` — `CommandParser`; unrelated to formatting, only error/missing-args behavior.

**Tests:**
- `tests/user_commands/tests.py:408-412` — `test_create_parser_kwargs` verifies kwargs pass through, currently only `epilog`. Add coverage that `formatter_class` can be supplied/overridden.
- `tests/admin_scripts/tests.py:1849` — `test_specific_help`; other help-output tests around 1865 and 2220. No existing formatter-specific test.

**Docs:**
- `docs/howto/custom-management-commands.txt:262` — documents `BaseCommand.create_parser(prog_name, subcommand, **kwargs)`; mention/update formatter customization here.
- `docs/ref/django-admin.txt` — general help output reference; no `DjangoHelpFormatter` mention found.

**Ruled out:**
- `tests/management/` does not exist; relevant tests live under `tests/user_commands/` and `tests/admin_scripts/`.
- No other formatter classes or `_split_lines`/`format_description` overrides in Django core.
- No docs currently reference `DjangoHelpFormatter`.
- `CommandParser.parse_args()`/`error()` are not involved.

**Conclusion:** Fix by changing `create_parser()` to default rather than force the formatter, e.g. `kwargs.setdefault("formatter_class", DjangoHelpFormatter)` before constructing `CommandParser`, allowing commands to pass `formatter_class=RawTextHelpFormatter` and preserve newlines. Add a regression test in `tests/user_commands/tests.py` and document the override.
