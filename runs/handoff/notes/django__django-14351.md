# Handoff: `Q.__or__` with related `__in` emits a multi-column subquery

**Issue.** `qs.annotate(Count("agent__property_groups")).filter(Q(agent__property_groups__in=pg_qs) | Q(agent__property_groups__count=0)).distinct()` raises `ProgrammingError: subquery must return only one column`; the `__in` subquery selects all default columns of the related model instead of the single join column. The `...__id__in=pg_qs.values_list("id", flat=True)` form works.

**Root cause / files.** `django/db/models/fields/related_lookups.py:46-91` (`RelatedIn.get_prep_lookup`). Lines 89-91 guard `self.rhs.clear_select_clause()` with `not getattr(self.lhs.field.target_field, 'primary_key', False)`. When the target field is the PK, the clause is never cleared, so the RHS queryset keeps `default_cols=True`. `has_select_fields` (`django/db/models/sql/query.py:244`) is then False, and `check_related_objects` (`query.py:1126`) accepts it. `Lookup.get_group_by_cols` (`django/db/models/lookups.py:117-121`) appends the RHS Query, and `BaseExpression.get_group_by_cols` (`django/db/models/expressions.py:348`) returns the whole Query, so the multi-column subquery lands in GROUP BY (`django/db/models/sql/compiler.py:63-148`). `SubqueryConstraint.as_sql` (`django/db/models/sql/where.py:233-248`) calls `set_values(self.targets)`, but the uncleared select still emits all columns.

**Ruled out.** `Exact.process_rhs` (`lookups.py:293-305`) — the lookup is `In`. `QuerySet.resolve_expression` (`django/db/models/query.py:1379-1385`) — it only rejects multi-field `values()`. `get_aggregation` subquery wrapping (`query.py:430-491`) — not the trigger.

**Tests/docs.** `tests/queries/tests.py:2497,2513` (`ToFieldTests`), `3566` (`ValuesSubqueryTests`), `3582` (`DoubleInSubqueryTests`), `726-743`; `tests/or_lookups/tests.py`; `tests/aggregation/tests.py:1257`; `tests/aggregation_regress/tests.py`. Docs: `docs/ref/models/querysets.txt` (`__in`), `docs/topics/db/queries.txt`.

**Conclusion.** Fix the guard at `related_lookups.py:89-91` so the select clause is cleared (or values set to targets) even when `target_field.primary_key`; add a regression test beside `ValuesSubqueryTests`.
