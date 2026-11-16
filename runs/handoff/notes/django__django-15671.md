## Handoff: overridable FormSet min/max error messages

**Issue:** `BaseFormSet` hardcodes the “too many forms” / “too few forms” validation messages, so they cannot be overridden through `error_messages`. Move them into `default_error_messages` and raise them via `self.error_messages`, matching `missing_management_form`.

**Key files/lines:**
- `django/forms/formsets.py:59-64` — `BaseFormSet.default_error_messages`; currently only `missing_management_form`.
- `django/forms/formsets.py:71-98` — `__init__` already collects messages from the class hierarchy and merges the `error_messages` argument into `self.error_messages`. This machinery needs no change.
- `django/forms/formsets.py:420-451` — `full_clean()` raises hardcoded `ngettext()` messages for `too_many_forms` (lines 427-435) and `too_few_forms` (lines 443-451). Replace these with lookups in `self.error_messages`, passing `num` through `ValidationError(..., params={"num": ...})`; use `ngettext`-compatible lazy messages in `default_error_messages` to preserve pluralization.
- `django/forms/formsets.py:398-399` — existing precedent using `self.error_messages["missing_management_form"]`.

**Tests/docs:**
- `tests/forms_tests/tests/test_formsets.py:381-407` (`test_formset_validate_max_flag`) and nearby `validate_min` tests around lines 409-465 exercise these paths.
- `tests/forms_tests/tests/test_formsets.py:910+` covers `max_num` behavior.
- Docs: `docs/topics/forms/formsets.txt` documents formset validation/`min_num`/`max_num`.

**Ruled out:** Existing tests do not assert the literal min/max message text (`grep` for `too few`/`too many`/`too_few`/`too_many` under `tests/forms_tests` found nothing), so no current assertions should break. Supporting `inlineformset_factory` overrides is explicitly out of scope per the issue.

**Conclusion:** Add `too_many_forms` and `too_few_forms` entries to `default_error_messages`, then use `self.error_messages` plus `params={"num": ...}` in `full_clean()` so overrides work through the `error_messages` argument. Add regression tests for overriding both messages.
