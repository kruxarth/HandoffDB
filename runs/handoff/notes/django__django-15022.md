# Handoff: unnecessary joins in admin changelist search

## Issue
Searching the admin changelist with several words stalls when `search_fields` span a reverse FK (e.g. `clientoffice__name`). Each word triggers a separate `queryset.filter(...)`, and each call adds another JOIN to the related table, so N words → N joins.

## Key code
- `django/contrib/admin/options.py:994-1046` — `ModelAdmin.get_search_results`. Builds one `Q` per word into `or_queries` (1032) and applies it with a single `queryset.filter(or_queries)` at **1041**. This is the origin of the repeated joins.
- `django/db/models/sql/query.py` — join-reuse machinery: `add_q`/`_add_q` (1395, 1406), `build_filter` (1241+), `setup_joins` (1479+), `join(..., reuse=...)` (963-990), `used_aliases` (174, 1276, 1417), `combine` (575-620) and its comment at **597** acknowledging duplicate non-m2m joins in AND cases, and `chain`/`filter_is_sticky` (351-353).

## Tests
- `tests/admin_changelist/tests.py`: 471 (`#15819` non-unique related), 492 (m2m at second level), 516 (`test_multiple_search_fields`), 567, 584, 601, 618.
- `tests/admin_views/tests.py`: 3573, 3608, 3653 (search behaviour).
- `tests/queries/tests.py`: ~3341 (`test_fk_reuse`, `test_revfk_noreuse`) — join-reuse contract.

## Ruled out
The ORM already reuses FK joins across chained `.filter()` calls (`test_fk_reuse`), so this is not a generic ORM defect. Naively merging the per-word filters into one AND is also wrong: `test_multiple_search_fields` requires words to match *different* related rows (reverse FK/M2M), and `test_revfk_noreuse` shows non-reuse is intentional there.

## Conclusion
Fix belongs in the admin search construction in `options.py` (dedupe/reuse joins per related path while preserving multi-valued OR semantics), not a blanket ORM change. Docs: `docs/ref/contrib/admin/index.rst` (`search_fields`) — not inspected. No code was modified; verification pending.
