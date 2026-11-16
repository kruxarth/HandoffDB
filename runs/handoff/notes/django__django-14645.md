## Handoff note: DecimalField crash on NaN with `max_value`

**Issue:** A form `DecimalField(max_value=12)` receiving `"NaN"` raises `decimal.InvalidOperation` instead of a validation error.

**Root cause / relevant code:**
- `django/forms/fields.py:325-380` — `DecimalField.to_python()` calls `decimal.Decimal(value)`, which accepts `"NaN"`, `"Inf"`, `"sNaN"`, etc. as valid `Decimal` objects. It never rejects non-finite values.
- `django/forms/fields.py:244-261` — `IntegerField.__init__` (parent) appends `MaxValueValidator`/`MinValueValidator` when `max_value`/`min_value` are set.
- `django/core/validators.py:346-372` — `BaseValidator.__call__` / `MaxValueValidator.compare` performs `a > b`; comparing `Decimal('NaN')` to an int raises `InvalidOperation`.
- `django/core/validators.py:426+` — `DecimalValidator` (digit checks) is appended separately; not the crash source here.
- `django/db/models/fields/__init__.py:1543-1556` — model `DecimalField.to_python` already catches `InvalidOperation`, but likewise does not reject NaN.

**Tests:** `tests/forms_tests/field_tests/test_decimalfield.py` (class at line 11; NaN/Infinity cases around lines 54-61, max_value cases lines 48-94) and `tests/model_fields/test_decimalfield.py:11`. Add a regression asserting `'Enter a number.'` for NaN/Infinity when `max_value` is set. Docs: `docs/releases/4.0.txt` (release note for the bug fix).

**Ruled out:** Conversion itself is not the failure — `Decimal('NaN')` constructs fine; the exception comes from validator comparison. `FloatField` already rejects NaN/Infinity (`test_floatfield.py`), so it is a useful precedent, not the bug.

**Conclusion:** Reject non-finite decimals (`value.is_finite()`) in the form `DecimalField.to_python`, raising `ValidationError` with the `invalid` message before validators run.
