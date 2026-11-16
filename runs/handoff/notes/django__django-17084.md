## Handoff note

**Issue:** In Django 4.2+, `QuerySet.aggregate()` over an annotation containing `Window(...)` emits SQL like `SUM(... OVER ...)`, causing PostgreSQL `GroupingError: aggregate function calls cannot contain window function calls`.

**Key code paths:**
- `django/db/models/sql/query.py:397-590` — `Query.get_aggregation()`. The 4.2 refactor inlines existing annotations into aggregate expressions via `Ref` replacements around **528-538**, so `Sum("cumul_DJR")` becomes `Sum(Coalesce(Window(...), 0.0))` instead of forcing a subquery.
- `django/db/models/sql/query.py:1926-1940` — `resolve_ref()`/`summarize` path relevant to resolving annotation refs during aggregation.
- `django/db/models/expressions.py:1698-1703` — `Window` correctly sets `contains_aggregate = False` and `contains_over_clause = True`; this is not the bug.
- `django/db/models/aggregates.py:30` — `Aggregate.window_compatible = True`; compatibility alone is not the issue.

**Related tests/docs:**
- `tests/expressions_window/tests.py` — window behavior; note aggregation-adjacent cases around **1106**, **1131**, **1334**, and `contains_aggregate` assertion at **1643**.
- `docs/releases/4.2.txt:275-276` — documents 4.2 aggregation changes against window functions.

**Ruled out:** `Window` metadata, `Aggregate.window_compatible`, and general `GROUP BY`/`HAVING`/`QUALIFY` splitting in `django/db/models/sql/compiler.py:87-92` and `django/db/models/sql/where.py:43-80` are not the direct cause.

**Conclusion:** Fix belongs in `get_aggregation()`: when aggregate expressions reference annotations containing over clauses, force a subquery (or raise `NotSupportedError`) rather than inlining the window expression into the outer aggregate. Add regression coverage in `tests/expressions_window/tests.py`.
