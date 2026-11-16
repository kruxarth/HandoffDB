## Handoff: Index/Constraint `__repr__` consistency

**Issue:** `Index`, `UniqueConstraint`, `CheckConstraint`, and `ExclusionConstraint` format `__repr__` differently. The task is to make their representations consistent without changing validation, SQL generation, deconstruction, or cloning behavior.

**Relevant code**
- `django/db/models/constraints.py:60` — `CheckConstraint.__repr__`; current expected format includes `check=... name=...`.
- `django/db/models/constraints.py:163` — `UniqueConstraint.__repr__`; formats fields/name differently.
- `django/db/models/indexes.py:171` — `Index.__repr__`; only reports `fields`/`expressions` and condition, without `name`.
- `django/contrib/postgres/constraints.py:157` — `ExclusionConstraint.__repr__`; reports name/expressions in its own order.
- Base validation/deconstruction lives in `django/db/models/constraints.py` (`BaseConstraint`) and `django/db/models/indexes.py` (`Index.__init__`), but those paths are not the bug.

**Tests**
- `tests/constraints/tests.py:60` — `CheckConstraint` repr expectation.
- `tests/constraints/tests.py:219` onward — `UniqueConstraint` repr expectations for fields, condition, include, opclasses, expressions.
- `tests/model_indexes/tests.py:17-44` — `Index` repr expectations for fields, condition, include, opclasses, expressions.
- `tests/postgres_tests/test_constraints.py:275` — `ExclusionConstraint` repr expectation.

**Docs**
- `docs/ref/models/constraints.txt` and `docs/ref/models/indexes.txt` document these APIs. No repr-format contract appears documented, so code/test updates should suffice.

**Ruled out**
- Not a `deconstruct()`/`clone()` issue.
- Not SQL-generation or backend DDL behavior.
- Not validation of `condition`, `fields`, `opclasses`, or `expressions`.
- Postgres-specific only for `ExclusionConstraint`; the inconsistency itself is shared.

**Conclusion:** The fix is confined to the four `__repr__` methods above. Align formatting across classes (class name plus relevant fields/expressions, condition, and name where applicable), then update the expected strings in the listed tests.
