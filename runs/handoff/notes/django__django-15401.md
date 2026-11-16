# Handoff: Deprecate unsaved objects in related filters

## Issue
`Foo.objects.filter(related_obj=bar)` with unsaved `bar` returned empty in 1.11 but behaves like `related_obj=None` from 2.0 onward, so it can return non-empty results. Intended resolution: deprecate passing unsaved model instances to related filters (per Simon Charette in #27985) and document it.

## Where the behavior lives
- `django/db/models/sql/query.py:1340-1480` — `build_filter()`: splits the lookup, calls `resolve_lookup_value()` (1155-1178) then `check_related_objects()` (called at 1407, defined 1205). This is the natural insertion point for a deprecation warning when the RHS is an unsaved `Model` on a related lookup. Note the iterator guard at 1404-1407.
- `django/db/models/sql/query.py:1179+` — `solve_lookup_type()`/`names_to_path()` determines whether the lookup crosses a relation.
- `django/db/models/fields/related_lookups.py:45+` — `get_normalized_value()` turns a `Model` into its PK value(s); unsaved instances yield `None` here, which is why the filter degrades to `IS NULL`.
- `django/db/models/fields/related.py:1955` — reverse relations already short-circuit on `obj.pk is None`; not the bug.

## Deprecation plumbing
`django/utils/deprecation.py:12` defines `RemovedInDjango50Warning` (project is 4.1 alpha, `django/__init__.py:3`).

## Tests
- `tests/queries/tests.py:3214-3222` — `test_exclude_unsaved_o2o_object`; asserts `exclude(staff=unsaved)` still returns rows. Must be revisited/kept green when warning is added.
- `tests/queries/tests.py:1478-1484` — unsaved instance passed to `update()`; unrelated path, ruled out.
- Likely new tests: `tests/queries/tests.py` and `tests/many_to_one/tests.py`.

## Docs
Add an entry under "Features deprecated in 4.1" in `docs/releases/4.1.txt:421+`; the timeline lives in `docs/internals/deprecation.txt`. `docs/ref/models/querysets.txt` has no current mention.

## Ruled out
Documentation-only fix; `related.py:1955`; unsaved-instance assignment checks in `tests/many_to_one/tests.py:638` and `tests/one_to_one/tests.py:153`.

## Conclusion
Implement a `RemovedInDjango50Warning` in `Query.build_filter`/`check_related_objects` (`django/db/models/sql/query.py`), add release-note entry, and update `tests/queries/tests.py`.
