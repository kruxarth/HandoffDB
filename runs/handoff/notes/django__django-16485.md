# Handoff: `floatformat()` crash on `"0.00"` with arg `0`

**Issue:** `floatformat("0.00", 0)` and `floatformat(Decimal("0.00"), 0)` raise `ValueError: valid range for prec is [1, MAX_PREC]`.

**Files/lines that matter:**
- `django/template/defaultfilters.py:96` — `def floatformat(text, arg=-1)`. The bug is in this function’s argument/precision handling after the docstring, especially the `precision == 0` / Decimal rounding branch. Both string and `Decimal` zero reach it; existing float cases like `floatformat(7.7, 0)` pass.
- `tests/template_tests/filter_tests/test_floatformat.py:34-56` — `FunctionTests.test_inputs` covers many precision cases but lacks string/`Decimal` zero with arg `0`. Add regression cases here.
- `docs/ref/templates/builtins.txt` — `floatformat` documentation; verify documented zero/rounding behavior.

**Ruled out:**
- Template parsing/filter registration; direct calls reproduce the crash.
- General float precision handling; existing `floatformat(7.7, 0)` and `floatformat(0.0)` tests pass.
- Useful git history; only snapshot commit `ed0602f` is present.

**Conclusion:** The defect is localized to `floatformat()`’s zero/precision branch. It appears to pass an invalid Decimal precision (`0`) when rounding a zero value supplied as a string or `Decimal`. The fix should special-case zero before precision validation and add tests for `"0.00"`, `Decimal("0.00")`, and `"0"` with arg `0`.
