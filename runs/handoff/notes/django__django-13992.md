# Handoff: `QuerySet.delete()` with `distinct(field)`

Issue: `Comment.objects.order_by('post_id', 'created_at').distinct('post_id').delete()` emitted `DELETE FROM comments;`, wiping the table, while `count()` respected `distinct`. Django version is 4.0 alpha.

Mattered code:
- `django/db/models/query.py:721-726` — `QuerySet.delete()` only rejects combined queries and limit/offset. It does not check `query.distinct_fields`; this is the safest guard point.
- `django/db/models/query.py:1150-1158` — `distinct()` stores `distinct_fields`; `:373-374` already rejects aggregate + distinct(fields); `:699` special-cases `in_bulk()`.
- `django/db/models/sql/compiler.py:1423-1464` — `SQLDeleteCompiler`. The `single_alias` fast path at `:1431-1439` builds plain `DELETE FROM table WHERE ...`, ignoring distinct/order_by. The subquery path is `:1440-1464`.
- `django/db/models/sql/subqueries.py:15-42` — `DeleteQuery.do_query()` / `delete_batch()`.

Tests/docs: `tests/delete/tests.py` (delete basics), `tests/delete_regress/tests.py:294-307` (`test_ticket_19102_distinct_on`, join case only; does not cover single-table fast path), `:244-246` (`values().delete()` guard), `tests/distinct_on_fields/tests.py:111-125` (existing NotImplemented checks). Docs: `docs/ref/models/querysets.txt` (`delete()`, `distinct()`), `docs/topics/db/queries.txt`.

Ruled out: combined-query and limit/offset guards already exist; aggregate/annotate + distinct(fields) already raise; `values().delete()` already raises `TypeError`. Not backend-specific.

Conclusion: simplest safe fix is rejecting `distinct_fields` in `QuerySet.delete()` with a clear error, plus a regression test; alternatively make `SQLDeleteCompiler` materialize a distinct PK subquery.
