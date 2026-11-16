# Handoff: strip unused annotations from `count()` queries

**Issue** — `Book.objects.annotate(Count('chapters')).count()` still emits the unused aggregate (joins/GROUP BY/subquery) even though it produces the same result as `Book.objects.count()`. Count should drop annotations not referenced by filters, other annotations, or ordering.

**Code path**
- `django/db/models/query.py:614-625` — `QuerySet.count()`/`acount()`; delegates to `Query.get_count()`.
- `django/db/models/sql/query.py:548-554` — `get_count()` clones, clears ordering, calls `get_aggregation(using, ["__count"])`.
- `django/db/models/sql/query.py:438-515` — `get_aggregation()`; existing annotations collected at 444-446, comment at 451-453 explains they force subqueries, masks handled at 474 and 502-511. This is where stripping belongs.
- `django/db/models/sql/query.py:1101-1111` — `add_annotation()`; mask updated at 1108-1110.
- `django/db/models/sql/query.py:209, 2363-2374` — `annotation_select_mask`, `set_annotation_mask()`, `append_annotation_mask()`: existing mechanism to reuse.
- `django/db/models/query_utils.py:353-363` — `refs_expression()` detects whether a lookup references an annotation; use to find annotations used by filters.
- `django/db/models/sql/where.py:190-241` — `WhereNode.get_source_expressions()`/`contains_aggregate()` for walking filter expressions.

**Tests/docs** — `tests/aggregation/models.py:23` (`Book`), `tests/aggregation/tests.py` (count tests at 665, 668, 1539), `tests/aggregation/test_filter_argument.py`; `docs/ref/models/querysets.txt:2403-2437`, `docs/topics/db/aggregation.txt:566`.

**Ruled out** — Annotation rebuilding in `change_aliases()` (`query.py:908`) is only alias relabelling, not the stripping point. Ad-hoc scripts failed due to missing `asgiref`; no tests ran and no code was edited.

**Conclusion** — Strip annotations in `Query.get_aggregation()` before count aggregation, keeping only those referenced by filters, other annotations, or ordering. No fix applied yet.
