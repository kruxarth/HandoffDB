## Handoff: Optimize `CreateModel` + `AlterModelManagers`

**Issue:** Migration optimization already folds `CreateModel` + `AlterModelOptions` into a single `CreateModel`, but the analogous `CreateModel` + `AlterModelManagers` case is not optimized.

**Key code:**
- `django/db/migrations/operations/models.py`
  - `CreateModel` starts line 41; its `reduce()` is lines 136–293.
  - Existing `AlterModelOptions` reduction branch is lines 156–166; it merges `options` into a new `CreateModel`.
  - `AlterModelManagers` is defined at line 732. There is no corresponding branch in `CreateModel.reduce()`.
  - `CreateModel` already accepts `managers=`, so the fix should return a new `CreateModel(..., managers=operation.managers)` when the names match.

**Tests:**
- `tests/migrations/test_optimizer.py:117–130` covers the existing `CreateModel` + `AlterModelOptions` optimization. Add an adjacent `test_create_alter_model_managers` asserting the two operations collapse to one `CreateModel` with `managers`.
- `tests/migrations/test_operations.py` and `tests/migrations/test_autodetector.py` reference `AlterModelManagers`; use them for operation/autodetector behavior, not optimizer coverage.

**Docs:** `docs/ref/migration-operations.txt` documents `CreateModel` and `AlterModelManagers`; update only if behavior wording needs clarification.

**Ruled out:** The generic `django/db/migrations/optimizer.py` does not special-case these operations; reduction belongs in `CreateModel.reduce()`. The existing `AlterModelOptions` branch does not cover managers because managers are a separate `CreateModel` argument and `AlterModelManagers` is a distinct operation.

**Conclusion:** Implement a new `isinstance(operation, AlterModelManagers)` branch in `CreateModel.reduce()` mirroring the `AlterModelOptions` branch, and add the optimizer regression test.
