## Handoff: `bulk_update()` does not resolve plain `F()` expressions

**Issue:** Assigning `F('field')` to an instance attribute and passing that field to `Model.objects.bulk_update()` emits SQL containing the literal string `'F(name)'` instead of the referenced column.

**Root cause / files:**
- `django/db/models/query.py`, `bulk_update()` around lines 640–720. At line 673 the guard `if not isinstance(attr, Expression):` is too narrow: plain `F` is not an `Expression` subclass, though it implements `resolve_expression()`. As a result it is wrapped as a literal `Value`, producing `CASE ... THEN 'F(name)'`.
- `django/db/models/query.py:20` already imports `Expression, F, ...`, so either including `F` in the type check or using duck typing is straightforward.
- `django/db/models/expressions.py`: `F`/`Combinable` expose `resolve_expression()`; `Case`/`When` around lines 595 and 694 already resolve expressions correctly. This rules out the SQL compiler/CASE construction as the primary bug.

**Tests/docs:**
- `tests/queries/test_bulk_update.py` is the relevant test module; `BulkUpdateNoteTests` starts near line 16, with simple/multiple-field coverage around lines 30–100. Add a regression test there assigning `note.note = F('misc')` (or similar), calling `bulk_update()`, refreshing, and asserting the resolved value/SQL.
- Docs: `docs/ref/models/querysets.txt` (`bulk_update()` section). No doc change likely required unless behavior wording needs clarification.

**Ruled out:** Backend-specific SQL generation and batch/CASE mechanics; the bad value is introduced before compilation by the narrow `isinstance(attr, Expression)` check.

**Conclusion:** Fix the line 673 check, preferably duck typing via `hasattr(attr, 'resolve_expression')` or `isinstance(attr, (Expression, F))`, and add the regression test in `tests/queries/test_bulk_update.py`.
