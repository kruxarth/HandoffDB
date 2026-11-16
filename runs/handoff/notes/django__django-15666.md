# Handoff: `QueryExpression` in a related model's `Meta.ordering` fails

**Issue** — `Album.Meta.ordering = ["artist"]` where `Musician.Meta.ordering = [F("instrument").asc(nulls_last=True)]` raises `TypeError: 'OrderBy' does not support indexing` when evaluating `Album.objects.all()`.

**Where it matters**
- `django/db/models/sql/compiler.py:869` `SQLCompiler.find_ordering_name()` — resolves a *string* name; its related-model branch (the `for item in opts.ordering:` loop near the end of the method, ~lines 925–950) pulls in the related model's ordering. Expression/`OrderBy` items there are not resolved against the related model's alias, so they fall through to `get_order_dir()`.
- `django/db/models/sql/query.py:2569` `get_order_dir()` indexes `field[0]` — the direct source of the `TypeError` when an `OrderBy` reaches it.
- `django/db/models/sql/compiler.py:308-420` `_order_by_pairs()`/`get_order_by()` already handle top-level expressions (`hasattr(field, "resolve_expression")` → `.asc()` → `resolve_expression`); that's why model-level expression ordering works but related-model ordering doesn't. Mirror that handling in the related-model branch.
- `django/db/models/expressions.py:~1501` `OrderBy`; `expressions.py:799-803` `F.asc`/`desc`; `query.py:2180` `Query.add_ordering()` (already accepts expressions).
- Docs: `docs/ref/models/options.txt` (`Meta.ordering`) — does not currently document expression ordering.

**Tests** — `tests/ordering/models.py:27-53` (`Article` ordering with `F`/`OrderBy`; `OrderedByFArticle` proxy) and `tests/ordering/tests.py:511` (`test_default_ordering_by_f_expression`), `:122` (`test_order_by_nulls_last`), `:494` (`test_related_ordering_duplicate_table_reference`). Add the regression test here: related model with an expression `Meta.ordering`, ordered through a FK.

**Ruled out** — `OrderBy`/`F` construction, `Query.add_ordering()` validation, `_order_by_pairs()` expression path, and `get_order_dir()` string handling.

**Conclusion** — the bug is in `find_ordering_name()`'s related-model ordering expansion. Tests could not be run in this environment (no `asgiref`/`sqlparse`, no network for pip).
