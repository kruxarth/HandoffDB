# Handoff: multiple `FilteredRelation` on same relation collapse into one JOIN

**Issue:** Two `FilteredRelation`s aliased to the same relation name with different `condition`s (e.g. `relation_zone` vs `relation_all`) produce only one JOIN; the second is silently dropped.

**Root cause / where to look:**
- `django/db/models/sql/query.py:1014-1044` `Query.join()` — reuse detection is `[a for a, j in self.alias_map.items() if (reuse is None or a in reuse) and j.equals(join)]`. Reuse happens before any new alias is created.
- `django/db/models/sql/datastructures.py` `Join.equals()` (and `__eq__`) — does not compare `filtered_relation`, so two joins differing only by condition compare equal and the second is reused.
- `query.py:792-830` `table_alias()` is where distinct aliases would be allocated (`filtered_relation.alias`).
- `query.py:1572-1601` `add_filtered_relation()` and `_filtered_relations` (246, 349) — correctly registers both aliases; not the bug.
- `query.py:1625-1700` path/lookup resolution and `django/db/models/fields/related.py:818-850`, `1764-1803` `get_path_info(filtered_relation=...)` — pass the relation through; ruled out.
- `django/db/models/sql/compiler.py:937-970` `get_from_clause()` just iterates `alias_map`; ruled out.

**Tests:** `tests/filtered_relation/tests.py` — add a case near `test_with_multiple_filter` (~line 228); `test_internal_queryset_alias_mapping` (~line 202) shows asserting on `str(queryset.query)` JOIN text.

**Docs:** `docs/ref/models/querysets.txt:3863-3901` (`FilteredRelation`); release notes `docs/releases/2.0.txt:297`, `3.2.txt:400`.

**Conclusion:** Not intended. Fix `Join.equals()` to also compare `filtered_relation` (conditions), so `Query.join()` creates a separate aliased JOIN per distinct `FilteredRelation`.
