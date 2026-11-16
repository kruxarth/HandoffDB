# Handoff: `QuerySet.update()` wrong on multi-table inheritance with multiple parents

**Issue:** `Child.objects.update(field_otherbase=55)` (Child inherits concrete `Base` and `OtherBase`) emits `UPDATE otherbase SET ... WHERE otherbase_id IN (<child pks>)`. The child pks are `base_ptr_id` values, not `otherbase_id`s, so the update hits unrelated `OtherBase` rows and never updates the Child's own second-parent table.

**Relevant code:**
- `django/db/models/query.py:981-999` — `QuerySet.update()`; chains to `UpdateQuery` and `add_update_values`.
- `django/db/models/sql/subqueries.py:80-99` — `add_update_values` splits values: fields whose `model` differs from the queryset's model are routed to `add_related_update`.
- `django/db/models/sql/subqueries.py:116-137` — `add_related_update` / `get_related_updates`; the related update query is filtered with `query.add_filter("pk__in", self.related_ids)`.
- `django/db/models/sql/compiler.py:1819-1857` — `SQLUpdateCompiler.pre_sql_setup`; computes `self.query.related_ids = idents` (child pk values) used above.

**Root cause:** `related_ids` holds the child's pk (`base_ptr_id`), but `get_related_updates` applies them as `pk__in` on the *other* parent model, whose pk (`otherbase_id`) is a different column. There is no per-parent link-field mapping.

**Tests/docs:** `tests/update/tests.py` (`SimpleTest.test_nonempty_update_with_inheritance`, `test_empty_update_with_inheritance` at lines 50-67) and `tests/update/models.py` (`A`, `B`, `C`, `D` — only a single concrete parent, so the bug is uncovered). `tests/model_inheritance/models.py` has multi-parent models (`Restaurant(Place, Rating)`), but `Rating` is abstract. No docs describe this path.

**Ruled out:** abstract-inheritance tests (`tests/model_inheritance/test_abstract_inheritance.py`), forms/migrations greps, and `Query.add_fields`/`set_select` — unrelated to the UPDATE path.

**Conclusion:** bug is in the related-update id mapping (`compiler.py:1857` feeding `subqueries.py:136-137`); fix must map child pks to each concrete parent's parent-link pk, not reuse `pk__in`. Add a multi-concrete-parent model to `tests/update/models.py` and a regression test in `tests/update/tests.py`.
