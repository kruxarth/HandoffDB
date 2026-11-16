# Handoff: optimize AlterFooTogether remove+add pairs

## Issue
Since #31503, changing `unique_together`/`index_together` emits a removal op and then an add op per option, so a model change yields four operations (`AlterUniqueTogether(set())`, `AlterIndexTogether(set())`, then the two re-adds). These should collapse to the two re-adds only.

## Where it matters
- `django/db/migrations/operations/models.py:470-548` — `AlterTogetherOptionOperation` (with `AlterUniqueTogether` at 532, `AlterIndexTogether` at 543) has no `reduce()`. `ModelOperation.reduce` (`models.py:33-38`) returns `not operation.references_model(...)`, so the optimizer stops scanning as soon as it hits *any* operation on the same model — which is exactly what happens between the removal and the re-add.
- `django/db/migrations/optimizer.py:1-260` — forward-scanning optimizer; no changes needed there.
- `django/db/migrations/autodetector.py:1186-1213` (removal generation), `1135-1176` (`_get_altered_foo_together_operations`), `150-200` (operation ordering) — generation order is intentional; do not change it.

## Tests / docs
- `tests/migrations/test_optimizer.py:150-215` (`_test_alter_alter_model`, `test_create_alter_foo_delete_model`) — already assert same-option collapse to the later op.
- `tests/migrations/test_autodetector.py:1663-1720` (`test_alter_field_and_foo_together`), `1397` (`test_empty_foo_together`), fixtures at `398-430`.
- `docs/ref/migration-operations.txt`, `docs/topics/migrations.txt`.

## Ruled out
Rewriting autodetector emission (breaks field-alteration ordering); touching `MigrationOptimizer`; changing `ModelOptionOperation`/`FieldOperation.reduce`.

## Conclusion
Add `AlterTogetherOptionOperation.reduce()`: return `[operation]` for the same option class/model (drop the stale removal), and return `True` (optimize across) for a *different* `AlterTogetherOptionOperation` on the same model, so the scan reaches the later same-option operation.
