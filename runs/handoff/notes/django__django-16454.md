# Handoff: management command subparsers lose error formatting

## Issue
`CommandParser` (`django/core/management/base.py:46-72`) stores `missing_args_message` and `called_from_command_line` in `__init__` (lines 53-58) and uses them in `error()` (lines 68-72) to raise `CommandError` instead of letting argparse print usage. Subparsers produced by `add_subparsers().add_parser()` are plain `ArgumentParser`s, so they never receive these flags; a missing required subparser argument raises `CommandError` and surfaces as a traceback rather than a usage message.

## Files / lines that matter
- `django/core/management/base.py:46-72` — the fix site. Add an `add_subparsers()` override that wraps `parser_class` with `functools.partial(parser_class, called_from_command_line=self.called_from_command_line)` when it is a `CommandParser` subclass. Add `from functools import partial` near line 7.
- `django/core/management/base.py:290` — `create_parser()` passes `called_from_command_line`; confirms where the flag originates.
- `django/core/management/__init__.py:366` and `django/core/management/utils.py:120` — other `CommandParser` constructions (`django-admin`, `call_command`); no change needed, but they show the flag is set in both paths.

## Tests / docs
- `tests/admin_scripts/tests.py` — parser/`CommandError` behavior tests; add a regression test with a fixture command under `tests/admin_scripts/management/commands/` defining a required subparser argument.
- `docs/howto/custom-management-commands.txt` — subcommand documentation.

## Ruled out
- Top-level missing-argument handling: works; the `missing_args_message` path at `base.py:60-66` is unrelated and not needed by subparsers.
- `error()` itself: correct — the subparser simply never sees `called_from_command_line`.
- Not specific to `call_command`; the CLI path fails too.

## Conclusion
Override `add_subparsers()` on `CommandParser` to propagate `called_from_command_line` into constructed subparsers, restoring argparse's usage-message-and-`SystemExit` behavior instead of an uncaught `CommandError`.
