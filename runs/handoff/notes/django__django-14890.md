# Handoff

**Issue:** `&` and `|` after `QuerySet.union()`, `intersection()`, or `difference()` are silently ignored; `combined_group & group1` and `combined_group | group3` produce the same SQL as `combined_group`. They should raise an exception instead of silently dropping the operator.

**Key code:**
- `django/db/models/query.py:327-336` (`__and__`) and `338-347` (`__or__`): both call `_merge_sanity_check()` then directly combine queries. They never check `self.query.combinator`, so the combinator state is lost/ignored.
- `django/db/models/query.py:1018-1027` (`_combinator_query`) and `1029-1058` (`union`, `intersection`, `difference`): these set `query.combinator` and `combined_queries`.
- `django/db/models/query.py:1372-1382` (`_merge_sanity_check`): only checks selected values/extra/annotations, not combinators.
- `django/db/models/query.py:~1426-1431` (`_not_support_combined_queries`): existing helper that raises `NotSupportedError`; the operators should use it.

**Tests/docs:** `tests/queries/test_qs_combinators.py` contains simple union/intersection/difference coverage around lines 20-72 but no `&`/`|` regression tests. Add tests asserting `NotSupportedError` after each combinator for both operators. `docs/ref/models/querysets.txt` documents `union()`/`intersection()`/`difference()` and combining querysets; update it if the limitation is documented.

**Ruled out:** SQL generation/compiler (`django/db/models/sql/compiler.py:462-511`, `get_combinator_sql`) is not dropping the operator; it never receives a new combinator because the QuerySet operators bypass combinator validation. `_merge_sanity_check` is unrelated.

**Conclusion:** Guard `__and__` and `__or__` with `_not_support_combined_queries(...)` so combining a combinator queryset raises `NotSupportedError`; add regression tests.
