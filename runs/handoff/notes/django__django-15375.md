## Handoff: aggregate default after annotate crashes

**Issue:** `Book.objects.annotate(idx=F("id")).aggregate(Sum("id", default=0))` crashes/generates invalid SQL (`SELECT FROM (SELECT ... COALESCE(SUM(...), ?) AS id__sum FROM ...) subquery`). Without `default`, and with explicit `Coalesce(Sum("id"), 0)`, it works.

**Key code:**
- `django/db/models/aggregates.py:26-33` — `Aggregate.__init__()` stores `default`.
- `django/db/models/aggregates.py:63-68` — `Aggregate.resolve_expression()` wraps the aggregate in `Coalesce(c, default)` and resets `c.default = None`. This wrapper is central to the bug.
- `django/db/models/query.py:398-430` — `QuerySet.aggregate()` adds the aggregate as a summary annotation (`is_summary=True`) and calls `get_aggregation()`.
- `django/db/models/sql/query.py:420-483` — `get_aggregation()` decides subquery/annotation masking. Lines 475-482 remove annotations whose `expression.is_summary` is true from `annotation_select_mask`; the `Coalesce` wrapper appears to carry/trigger summary handling, leaving the outer query with an empty SELECT.
- `django/db/models/sql/query.py:1035-1042`, `2173-2178` — annotation insertion and mask handling.
- `django/db/models/expressions.py:155`, `247`, `514` — `is_summary` defaults/set during resolution.

**Tests/docs:** Existing default tests in `tests/aggregation/tests.py:1415-1439` and `1627`; add regression for annotate-then-aggregate with `default`. Docs: `docs/topics/db/aggregation.txt`, `docs/ref/models/querysets.txt`.

**Ruled out:** Backend-specific behavior (reproduced on SQLite; reported on PostgreSQL), long-form `Coalesce`, and plain aggregate without `default`.

**Conclusion:** Bug is the interaction between `Aggregate.resolve_expression()`’s `Coalesce` default wrapper and `Query.get_aggregation()`’s `is_summary`/annotation-mask filtering. Fix should preserve correct summary state and ensure the wrapped aggregate remains selected in the outer query.
