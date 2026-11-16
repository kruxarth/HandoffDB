## Handoff note: `__in` subquery not cleared after `alias()` following `annotate()`

**Issue:** `Publisher.objects.filter(book__in=long_books_qs)` raises `OperationalError: sub-select returns 10 columns - expected 1` when `long_books_qs` is `.annotate(book_annotate=Value(1)).alias(book_alias=Value(1))`.

**Root cause / key code:** `django/db/models/sql/query.py:266-271` — `Query.has_select_fields` returns `bool(self.select or self.annotation_select_mask or self.extra_select_mask)`. The related-lookup path (`django/db/models/fields/related_lookups.py:93-96`, `RelatedIn`) only calls `self.rhs.clear_select_clause()` / `add_fields(["pk"])` when `has_select_fields` is falsy. `.annotate()` adds `book_annotate` to the mask; `.alias()` then runs `set_annotation_mask(set(self.annotation_select).difference({alias}))` at `query.py:1117-1118`, leaving a non-empty `annotation_select_mask` even though `default_cols` is still `True`. So `has_select_fields` wrongly reports True, the default model columns plus annotation are retained, and the subquery selects 10 columns. Also relevant: `Query.clear_select_clause` (`query.py:2092-2099`), `add_fields` (`query.py:2124`), `set_annotation_mask` (`query.py:2357`), `annotation_select` (`query.py:2435`).

**Conclusion:** `has_select_fields` must also require `not self.default_cols`, i.e. return True only when explicit select/annotation/extra fields exist and default columns are off.

**Ruled out:** `alias()`/`_annotate()` in `django/db/models/query.py:1586-1650` (mask handling is intentional); `add_annotation` (`query.py:1109`); `SubqueryConstraint.as_sql`/`set_values` (`query.py:335-350`, `2383`) — correct once `has_select_fields` is right; the `Exact` lookup's similar check (`lookups.py:328-336`) has the same latent issue.

**Tests/docs:** add reproduction to `tests/annotations/tests.py` (near `test_basic_alias`, ~line 1184); related alias tests in `tests/lookup/tests.py:1298`; no release note needed yet.

**Remaining:** apply the `has_select_fields` fix and run the new test.
