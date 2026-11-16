## Handoff: squashed migration not marked unapplied

**Issue:** Unapplying a squashed (replacement) migration leaves the squashed migration recorded as applied in `django_migrations`; only its `replaces` entries are recorded unapplied. Replaced files still on disk make the squashed migration the graph node used for the backwards plan.

**Key code**
- `django/db/migrations/executor.py` — `unapply_migration()`: the `if migration.replaces:` branch records each replaced `(app_label, name)` via `record_unapplied()` but never records `migration` itself. The apply counterpart is in `apply_migration()` (squash-related comments at lines 270–272); it records the squashed migration too, which is why the row exists to go stale.
- `django/db/migrations/recorder.py:84-92` — `record_applied()` / `record_unapplied()`; note they delete/insert rows keyed by `(app, name)`.
- `django/db/migrations/loader.py:261-262, 301` — replacement/partial-squash handling in `build_graph()`; it derives a squashed migration's applied status from its `replaces` targets.
- `django/db/migrations/graph.py:47` — replacement-node removal.

**Tests**
- `tests/migrations/test_executor.py:613` `test_apply_all_replaced_marks_replacement_as_applied` and `:636` are the model for a regression test; `:68` covers running a squash.
- `tests/migrations/test_commands.py:900` `test_migrate_record_replaced` asserts the squashed name is recorded applied after `migrate` — the state that must be cleared on unapply.
- Fixture: `tests/migrations/test_migrations_squashed/` (`0001_squashed_0002.py` replacing `0001_initial`/`0002_second`).
- Docs: `docs/topics/migrations.txt` (squashing migrations) describes replacement semantics.

**Ruled out:** loader/graph replacement resolution (correctly derives applied state from replaced rows), the apply path (covered by existing tests), and `showmigrations`/`sqlmigrate` command output.

**Conclusion:** In `unapply_migration()`, when `migration.replaces` is set, also call `record_unapplied(migration.app_label, migration.name)`. Add a test applying then unapplying the squashed fixture and asserting the squashed key is absent from `recorder.applied_migrations()`.
