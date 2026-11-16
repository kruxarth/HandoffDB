# Handoff: Prune nonexistent migrations from `django_migrations`

## Issue
After `squashmigrations` and deleting replaced files, stale rows remain in `django_migrations`. A newly created migration reusing an old name (e.g. `0002_blah`) is then treated as already applied and silently skipped. Desired: automatically remove records for migrations that no longer exist, **but keep records for migrations listed in another migration's `replaces`**, so an unapplied squash isn't reapplied.

## Key code
- `django/db/migrations/recorder.py:9-80` — `MigrationRecorder`: `has_table()` (53), `migration_qs`, `applied_migrations()` (72), `record_applied`/`record_unapplied`. Natural home for a prune/delete helper.
- `django/db/migrations/loader.py:220-223` — loads `applied_migrations` from recorder; `:244-250` — squashed-migration logic that injects/pops replaced keys; `:296-297` — `check_consistent_history`. Pruning must not break the `replaces` handling here.
- `django/db/migrations/executor.py:16-20` — constructs loader+recorder; `:30` uses `loader.applied_migrations`.
- `django/core/management/commands/migrate.py` — command entry point; likely place to trigger pruning after the graph is built (agent's conclusion).

## Tests
- `tests/migrations/test_loader.py` — `RecorderTests` (top), `test_loading_squashed` (249), `test_loading_squashed_complex` (268), history checks (~386).
- `tests/migrations/test_executor.py` — `test_apply_all_replaced_marks_replacement_as_applied` (~649).
- `tests/migrations/test_commands.py:909-1004` — `test_migrate_record_replaced` and related.
- `tests/migrations/test_base.py` — `record_applied` helper.

## Docs
`docs/topics/migrations.txt:625-700` (squashing/`replaces`); `docs/releases/4.1.txt` (add release note); `docs/intro/tutorial02.txt:346`.

## Ruled out
No existing pruning feature (`grep prune` — no hits). Pruning at `loader.py:220-223` alone is unsafe; it must be aware of `replaces` (lines 244-250). Not a loader-graph bug.

## Conclusion
Add a recorder-level deletion of rows absent from the loaded graph, excluding names in any migration's `replaces`; invoke from `migrate`. Update `test_commands.py`/`test_loader.py` and release notes.
