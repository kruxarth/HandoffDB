# Handoff: Migration optimizer does not reduce multiple `AlterField`

## Issue
`MigrationOptimizer.optimize()` reduces a chain beginning with `AddField` + repeated `AlterField`, but does not reduce consecutive `AlterField` operations when the `AddField` is absent (e.g. separated by a non-elidable operation or across migrations). This is because `AlterField.reduce()` does not handle a following `AlterField` on the same field.

## Relevant code
- `django/db/migrations/operations/fields.py`
  - `FieldOperation.is_same_field_operation()` lines 25–29 — used to detect same model/field.
  - `AlterField` class, roughly lines 196–250; `reduce()` around lines 233–245. This is the fix site. It currently handles `CreateModel`/`AddField` cases but not `AlterField`.
  - `preserve_default` handling lines 204–236 — keep it when merging.
- `django/db/migrations/optimizer.py` lines 12–30 — documents that same-field operations are boundaries; no change needed here.

## Tests/docs
- `tests/migrations/test_optimizer.py`: existing AlterField cases at lines 645 (`test_create_model_alter_field`), 785 (AlterField into AddField), 813 (RemoveField absorbs AlterField), and 859/1082. Add a regression test for two/three consecutive `AlterField` operations optimizing to the last one.
- Docs: `docs/ref/migration-operations.txt` and `docs/topics/migrations.txt` describe optimizer behavior; document only if behavior is intentionally left unchanged.

## Ruled out
Optimizer traversal/boundary logic is not at fault: the `AddField`-prefixed chain reduces correctly because `AddField.reduce()` absorbs subsequent `AlterField`s. `preserve_default` is not the cause; it only needs preserving during the merge.

## Conclusion
This is unintended. Add an `AlterField`/`AlterField` branch in `AlterField.reduce()` using `is_same_field_operation()`, returning the later operation (latest field plus `preserve_default`), and add the regression test.
