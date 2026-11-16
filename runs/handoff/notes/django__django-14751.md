# Handoff: makemigrations scriptability

**Issue:** `makemigrations` isn't script-friendly — progress output goes to stdout, and there's no structured way to learn which migration files were created (e.g. to copy them out of a Docker container).

**Code that matters**
- `django/core/management/commands/makemigrations.py` — the whole `Command`; `add_arguments()` defines `app_label` args plus `--dry-run/--merge/--empty/--check/--name/--no-input` (roughly lines 26–90). All user-facing output is emitted via `self.stdout.write(...)` inside `handle()`; there is no `self.stderr` usage anywhere in the file.
- `django/core/management/commands/migrate.py` lines 163–294 — same pattern (`self.stdout.write` for headings, plan, "Applying …"), confirming stream routing is a project-wide convention, not local to `makemigrations`.

**Tests**
- `tests/migrations/test_commands.py`: `MakeMigrationsTests` starts at line 1047; `test_makemigrations_check` ~1820; `test_makemigrations_migration_path_output` ~1830 and `test_makemigrations_migration_path_output_valueerror` ~1844 already assert that created migration paths are printed to `stdout` (relative, falling back to absolute on `ValueError`).

**Docs**
- `docs/ref/django-admin.txt` lines 776–830 (`makemigrations` options).
- `docs/releases/4.1.txt` lines 208–212 (recent `--no-input` logging change).

**Ruled out**
- No existing `stderr` plumbing or script-oriented flag in `makemigrations`.
- Missing file-path output: it already exists and is covered by tests, so the "structured way to know created files" half of the request is already satisfied by capturing `stdout`.

**Conclusion**
The created file paths are already written to `stdout` and testable; the remaining request (progress on `stderr`) would change output behavior across management commands and is not localized. Prefer documenting "capture stdout / use `verbosity=0`" rather than rerouting streams.
