# Handoff: admin delete crashes after M2M search

## Issue
Deleting selected rows from an admin changelist crashes with `TypeError: Cannot call delete() after .distinct().` when `search_fields` spans a many-to-many (`authors__email`). Searching an M2M forces `.distinct()` on the changelist queryset, which is then handed to the delete action and rejected by the ORM.

## Path (all in this repo)
- `django/contrib/admin/views/main.py:442-492` — `ChangeList.get_queryset()` returns `qs.distinct()` at line 492 when `search_use_distinct` is true (set by `ModelAdmin.get_search_results`, `options.py:1022-1035`).
- `django/contrib/admin/options.py:1721` and `:1737` — `changelist_view()` passes `cl.get_queryset(request)` into `response_action()`.
- `django/contrib/admin/options.py:1353-1415` — `response_action()` calls the action with that queryset.
- `django/contrib/admin/actions.py:45` — `delete_selected` calls `modeladmin.delete_queryset(request, queryset)`.
- `django/contrib/admin/options.py:1105-1107` — `delete_queryset()` does `queryset.delete()`, which hits the guard.
- `django/db/models/query.py:725-728` — the `TypeError` is raised intentionally.

## Tests
- `tests/admin_views/test_actions.py:43` — `test_model_admin_default_delete_action` (natural place for a regression test).
- `tests/admin_changelist/tests.py:444` — `test_distinct_for_many_to_many_at_second_level_in_search_fields` (distinct behavior to preserve).
- `tests/delete_regress/tests.py:361` — asserts the ORM guard is intentional.

## Docs
- `docs/ref/models/querysets.txt:2655-2662` — `delete()` limitations.
- `docs/releases/3.2.1.txt` — related admin/search fixes.

## Ruled out
Changing `QuerySet.delete()` / removing the distinct guard — intentional, covered by `delete_regress`. No upstream patch shape was confirmed; no regression test was run.

## Conclusion
Fix belongs in the admin delete path: strip `distinct` (or delete by collected PKs) before `queryset.delete()`, then add an admin regression test for delete-after-M2M-search.
