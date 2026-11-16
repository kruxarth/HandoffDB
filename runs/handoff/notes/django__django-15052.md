# Handoff: filtered aggregate with `Exists` crashes

The issue: `Book.objects.values("publisher").aggregate(max_rating=Max("rating", filter=Exists(...)))` raises `TypeError: can only concatenate list (not "tuple") to list`.

Mattering code:
- `django/db/models/aggregates.py:79-93` — `Aggregate.as_sql`; line 90 `return sql, params + filter_params` is the crash site. `params` is a list while `filter_params` from `Exists` is a tuple. Fix by returning `sql, (*params, *filter_params)`.
- `django/db/models/expressions.py:1116-1195` — `Subquery`/`Exists.as_sql`, especially `Exists.as_sql` around 1185-1199. This explains the tuple/list mismatch but is not the root cause.
- `django/db/models/expressions.py:700-730` — `Func.as_sql`, relevant to parameter container types.

Tests:
- `tests/aggregation/test_filter_argument.py`, especially `test_filtered_aggregate_with_exists` around line 146 (traceback line). This is the regression test location.

Docs:
- `docs/topics/db/aggregation.txt` for filtered aggregates.
- `docs/ref/models/expressions.txt` for `Exists`/`Subquery`.

Ruled out: `Exists`/`Subquery` SQL generation and backend `supports_aggregate_filter_clause` handling. Filter SQL is generated successfully; failure occurs only when `Aggregate.as_sql` concatenates parameters. The query compiler/setup path in the traceback is incidental.

Conclusion: parameter concatenation bug in `Aggregate.as_sql`; apply tuple-unpacking patch and run the aggregation filter tests.
