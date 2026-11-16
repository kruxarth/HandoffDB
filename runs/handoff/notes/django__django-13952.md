# Handoff: migrate -v2 verbose output not capturable

## Issue
`migrate --verbosity 2` prints "Running pre-migrate/post-migrate handlers for application …" via bare `print()`, so output goes to `sys.stdout` and bypasses `call_command(..., stdout=...)`. Reported from PR #13890 review.

## Files and line ranges
- `django/core/management/sql.py:18-32` — `emit_pre_migrate_signal()`: `print(...)` at line 24 when `verbosity >= 2`. Needs a `stdout` argument.
- `django/core/management/sql.py:35+` — `emit_post_migrate_signal()`: same pattern (identical `print()` guard); needs the same treatment.
- `django/core/management/commands/migrate.py:203` — `emit_pre_migrate_signal(self.verbosity, self.interactive, connection.alias, ...)`; must pass `self.stdout`.
- `django/core/management/commands/migrate.py:268` — `emit_post_migrate_signal(...)`; must pass `self.stdout`.
- `django/core/management/commands/flush.py:80` — `emit_post_migrate_signal(verbosity, interactive, database)`; also affected, pass `self.stdout`.
- `django/test/testcases.py:933` — `emit_post_migrate_signal(verbosity=0, ...)`; verbosity 0 means no printing, but the call site must stay compatible with any signature change (give `stdout` a default or pass `sys.stdout`).

## Tests
- `tests/migrate_signals/tests.py` — checks signal kwargs (`SIGNAL_ARGS`, lines 8, 63-118) but never asserts stdout capture; extend here with a `call_command('migrate', verbosity=2, stdout=out)` assertion.
- `tests/admin_scripts/tests.py` — existing `StringIO` stdout-capture patterns to mirror.
- No `tests/flush/` directory exists.

## Ruled out
`tests/testcases.py` call uses `verbosity=0`, so it emits nothing; no behavioral change needed there. Flush's verbosity path shares the same bug rather than being a separate cause.

## Conclusion
Thread a `stdout` parameter through both emit functions, replace `print()` with `stdout.write()`, and pass `self.stdout` from `migrate` and `flush`.
