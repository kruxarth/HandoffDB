# Handoff: OR-combined queryset ignores subsequent `.filter()`

**Issue** — `qs = Buss.objects.filter(jurisdiction='GB') | ...exclude(name__in=qs.values_list('name'))` (twice); then `qs.filter(jurisdiction='GB')` returns 34 rows instead of 8 and the SQL is unchanged. Filtering by a different value (`US`) works. Reported on 3.2.1; repo is 4.0 alpha (`django/__init__.py:4`).

**Root cause / files**
- `django/utils/tree.py:78` `Node.add()` — the early dedup `if data in self.children: return data` (inside the method, ~lines 92–99) returns the existing child and never appends the new clause when the node's connector (`OR`) differs from `conn_type` (`AND`). Reproduced standalone with dummy leaves: after two OR combines plus one AND filter, `children` stayed at 3.
- Leaves compare equal because `Lookup.identity`/`__eq__`/`__hash__` (`django/db/models/lookups.py:150–160`) is value-based, so the duplicate `jurisdiction='GB'` lookup matches the one already under the OR node.
- `WhereNode` subclasses `Node` (`django/db/models/sql/where.py:15`); `Q` too (`django/db/models/query_utils.py:29`). Filter path: `Query.add_filter` 1360 → `add_q` 1363 → `_add_q` 1383 → `target_clause.add(child, connector)` 1401/1423.

**Ruled out** — `Query.combine` (`django/db/models/sql/query.py:557–640`) and `WhereNode.as_sql` emit correct SQL; the new clause simply never reaches the WHERE tree. Not a `Q()`-vs-`exclude()` problem, and unrelated to subquery/`split_exclude` generation (`query.py:1744`), since the emitted SQL is valid.

**Tests/docs** — add a regression test in `tests/queries/tests.py`, class `DisjunctiveFilterTests` (line 1719), next to `test_ticket8283`; node-level semantics live in `tests/utils_tests/test_tree.py`. Docs: `docs/ref/models/querysets.md` (combining querysets) and `docs/topics/db/queries.md` (Q objects). Note the env lacks `asgiref`, so the suite can't run yet.

**Conclusion** — Fix `Node.add()` so the dedup only applies when the node connector matches `conn_type`: an AND-ed clause must be appended even if an equal leaf already exists under an OR node.
