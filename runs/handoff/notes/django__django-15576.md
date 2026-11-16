## Handoff note

**Issue:** `.exists()` on `distinct()` querysets unnecessarily selects all model fields. The prior fix for #18414 made `Query.exists()` skip `clear_select_clause()` whenever `q.distinct` is true, so even non-sliced distinct querysets keep their full SELECT list. The intended behavior is to preserve fields only when `q.distinct` and the query is sliced (`q.high_mark is not None or q.low_mark is not None`, equivalent to `q.is_sliced`).

**Files/lines that matter:**
- `django/db/models/sql/query.py:563-573` — `Query.exists()`. The guard `if not q.distinct:` at line 565 prevents `q.clear_select_clause()` at line 573 for all distinct queries. This is the one-line logic to change: clear select unless `q.distinct and q.is_sliced`.
- `django/db/models/sql/query.py:2084` — `is_sliced` property, confirming slice detection via `low_mark`/`high_mark`.
- `tests/queries/tests.py:2218-2245` — `ExistsSql.test_exists` and `test_ticket_18414`. Existing tests cover correctness for `distinct()` and sliced `distinct()` but only assert boolean results, not selected columns.

**Related docs:** `docs/ref/models/querysets.txt` documents `QuerySet.exists()`; no behavior/API change is expected, so docs likely need no edit.

**Ruled out:** `get_aggregation()` around `query.py:440-487` is unrelated. The non-distinct `exists()` path, `group_by is True` handling, combined-query handling, and ordering/limit clearing are unaffected. `distinct_fields` behavior should remain covered by existing tests.

**Conclusion:** Fix the guard in `exists()` so distinct, non-sliced querysets clear their select clause, while sliced distinct querysets retain fields. Add a regression assertion in `ExistsSql` using `CaptureQueriesContext` to verify `.distinct().exists()` omits model columns and `.distinct()[1:3].exists()` retains them.
