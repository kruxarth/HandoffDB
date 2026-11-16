# Handoff: `Q() & Exists()` raises `TypeError`

**Issue:** `Q() & Exists(qs)` raises `TypeError`; `Exists(qs) & Q()` works. The operators should commute.

**Findings:**
- `django/db/models/query_utils.py:28-71`: `Q._combine()` (`42-58`) rejects any `other` that is not a `Q`. `Q.__and__` (`64-65`) and `Q.__or__` (`61-62`) call it directly, so Python never reaches a reflected operation. `Q` also lacks `__rand__`/`__ror__`. This is the root cause.
- `django/db/models/expressions.py:33-117`: `Combinable` already handles boolean `__and__`/`__rand__` and returns `Q` when both operands are conditional. Its `_combine()` (`58-68`) is for arithmetic/bitwise combinations and is not at fault.
- `Exists` at `django/db/models/expressions.py:1150-1188` is conditional and works from the left side; no change needed there.

**Tests/docs:**
- `tests/queries/test_q.py:7-28` cover `Q`/`Q` commutativity; `tests/queries/test_q.py:32-36` asserts `Q & arbitrary_object` raises `TypeError` with `str(obj)`, which must be preserved.
- `tests/expressions/tests.py` `BasicExpressionsTests.test_exists_in_filter` (~line 763) covers `Exists` filtering; add a `Q`/`Exists` commutation regression test there or in `tests/queries/test_q.py`.
- Docs: `docs/ref/models/querysets.txt` (Q objects) and `docs/ref/models/expressions.txt` (`Exists`).

**Ruled out:** `Exists`/`Combinable`, `CombinedExpression`, SQL compilation, and query filtering.

**Conclusion:** Fix `Q` by making `_combine()` accept conditional expressions (`getattr(other, "conditional", False)`) and adding `Q.__rand__`/`Q.__ror__` delegating to `_combine`, while retaining `TypeError` for non-conditional non-`Q` objects. Then `Q() & Exists()` should return a valid conditional expression.
