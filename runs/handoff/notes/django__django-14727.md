# Handoff: partially applied squashed migration as target raises bare NodeNotFoundError

## Issue
Naming an incompletely applied squashed (replacement) migration as a migrate target fails with a bare `NodeNotFoundError`. Root cause: in `MigrationLoader.build_graph()`, when a replacement migration's `replaces` set is only partially applied, the replacement is removed from the graph and the replaced nodes are remapped back. If the user then targets the squash name, `get_migration_by_prefix()`/graph lookup fails because that node no longer exists. The issue's cited lines 205-208 (`add_external_dependencies`) are stale; the real code is `django/db/migrations/loader.py:245-256`.

## Files that matter
- `django/db/migrations/loader.py:207-256` — `build_graph()`; the partial-application branch that drops the replacement node and calls `remove_replacement_node` (lines ~253-256). This is where a warning or enriched error belongs.
- `django/db/migrations/loader.py:257-278` — existing `NodeNotFoundError` enrichment for #23556; only handles a *replaced* node missing, not the squash itself being the missing target.
- `django/db/migrations/graph.py:122-168` — `remove_replaced_nodes`/`remove_replacement_node`; no change needed.

## Tests and docs
- `tests/migrations/test_loader.py:247-264` (`test_loading_squashed`) — closest regression-test pattern; add a case applying one child then targeting the squash name.
- Fixtures: `tests/migrations/test_migrations_squashed/`, `test_migrations_squashed_complex/`, `test_migrations_squashed_ref_squashed/`.
- `tests/migrations/test_executor.py:619` — partial-application comment.
- `tests/migrations/test_commands.py:338-369, 545-591` — squash/plan behavior.
- Docs: `docs/topics/migrations.txt:653-712` (squashing), `docs/releases/4.0.txt:272` (Migrations section).

## Ruled out
Target parsing in `django/core/management/commands/migrate.py:127-136` and `MigrationExecutor.migration_plan()` (`executor.py:22-58`); the failure occurs earlier, at graph build. `graph.py`'s own `NodeNotFoundError` sites (133, 168, 204, 214) are not the trigger.

## Conclusion
Fix belongs in `loader.py` around lines 245-256: warn (or raise a descriptive error) when a replacement migration is excluded because its replaced set is partially applied, so users understand why the squash target is missing. Add a regression test in `test_loader.py` near line 264.
