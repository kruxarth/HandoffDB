## Handoff: ModelChoiceField invalid-choice message

**Issue:** `ModelChoiceField` raises `invalid_choice` without the rejected value, unlike `ChoiceField`/`ModelMultipleChoiceField`.

**Key code:** `django/forms/models.py`
- `ModelChoiceField` class: lines 1186–1299.
- `default_error_messages['invalid_choice']`: lines 1190–1193. It lacks `%(value)s`.
- `ModelChoiceField.to_python()`: lines 1278–1287; line 1287 raises `ValidationError` with no `params`.
- `ModelMultipleChoiceField` already interpolates `%(value)s`: message at 1307–1308, raise at 1368–1369.
- `ChoiceField` already interpolates `%(value)s`: `django/forms/fields.py` lines 767, 806–807.

**Tests:** Existing expectations use the old wording and will need updating:
- `tests/model_forms/test_modelchoicefield.py` lines 54, 62, 219.
- `tests/model_forms/tests.py` line 1678.

**Docs:** No docs were inspected in this session. Relevant docs are likely `docs/ref/forms/fields.txt` (`ModelChoiceField` error messages) and `docs/topics/forms/modelforms.txt`.

**Ruled out:** Inline-form `invalid_choice` at `models.py` 1107/1134 is unrelated. `ChoiceField` and `ModelMultipleChoiceField` already include the value, so the defect is isolated to `ModelChoiceField`.

**Conclusion/fix:** Update `ModelChoiceField.default_error_messages['invalid_choice']` to include `%(value)s`, and pass `params={'value': value}` when raising at line 1287. Update the listed test expectations. No behavioral change to choice validation is needed.
