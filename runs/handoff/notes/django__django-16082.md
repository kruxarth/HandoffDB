# Handoff: MOD output_field for mixed Decimal/Integer expressions

**Issue.** `F("decimal") % F("integer")` (`CombinedExpression` with `Combinable.MOD`) did not infer `DecimalField` output_field like ADD/SUB/MUL/DIV; mixed Decimal/Integer MOD should promote to Decimal.

**Code that matters.**
- `django/db/models/expressions.py`: `Combinable.MOD` ~49–51; `_combine` ~91/145; the type-inference table `_connector_combinations` ~496–570. MOD appears at lines 519 and 562; the mixed numeric combination list containing `(DecimalField, IntegerField, DecimalField)` and reverse is the place to verify/correct.
- `django/db/models/functions/math.py:124` (`Mod`) and `django/db/models/functions/mixins.py` (`FixDecimalInputMixin`) were inspected for the `Mod()` function path.

**Tests/docs.**
- `tests/expressions/tests.py`: modulo tests at 1404–1414 (`test_lefthand_modulo`, `test_lefthand_modulo_null`) and 1526–1530 (`test_right_hand_modulo`) only exercise integers. Add Decimal/Integer mixed `%` regression cases and assert `DecimalField` output.
- `tests/db_functions/math/test_mod.py` covers `Mod()` Decimal/Decimal, Float, Integer; add mixed Decimal/Integer only if the function path is changed.
- Docs: `docs/ref/models/expressions.md` (arithmetic expressions/output_field); `docs/ref/models/database-functions.md#mod`.

**Ruled out.** Backend SQL casting, the `Mod()` function’s output_field (it already inherits `NumericOutputFieldMixin`), and PostgreSQL float-to-decimal casting in `FixDecimalInputMixin` are not the cause of the `CombinedExpression` `%` failure.

**Conclusion.** Fix `CombinedExpression` output-field inference in `_connector_combinations` so MOD’s mixed Decimal/Integer case resolves to `DecimalField`, matching other numeric operators; add regression tests in `tests/expressions/tests.py`.
