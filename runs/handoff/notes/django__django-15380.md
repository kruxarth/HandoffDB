## Handoff note

**Issue:** `makemigrations` crashes with `KeyError: ('test_one', 'mymodel')` when renaming a model and one of its fields in the same autodetection pass. Traceback points to `django/db/migrations/autodetector.py`, `generate_renamed_fields()`.

**Relevant code:** `django/db/migrations/autodetector.py:821-871` implements `generate_renamed_fields()`. The loop over `new_field_keys - old_field_keys` computes `old_model_name = self.renamed_models.get((app_label, model_name), model_name)` at ~line 825, then looks up `self.to_state.models[app_label, old_model_name]`; after a model rename, `to_state` contains the **new** model name, so this lookup raises `KeyError`. `old_model_name` should only be used for `from_state`; `model_name` should be used for `to_state`. Supporting logic: `_prepare_field_lists()` at lines 213-231 builds old/new field keys using `renamed_models`; `generate_renamed_models()` at lines 466-512 populates that mapping.

**Tests:** `tests/migrations/test_autodetector.py` — `test_rename_field` (~855), `test_rename_model_with_renamed_rel_field` (~1111, covers related-field rename but not a direct field on the renamed model), and fixtures at ~56, ~217, ~369. Add a regression test renaming a model and a non-relational field together with `ask_rename_model`/`ask_rename`.

**Docs:** `docs/ref/migration-operations.txt` and `docs/topics/migrations.txt` are relevant user-facing docs; no doc change appears needed.

**Ruled out:** Questioner behavior and rename detection are working; issue is not limited to through/related fields. Regression commit `aa4acc164d1247c0de515c959f7b09648b57dc42` is unavailable in this snapshot (`git log` shows only `28e8fcf snapshot`), so it could not be inspected.

**Conclusion:** Fix `generate_renamed_fields()` to index `to_state` with the new `model_name`, retaining `old_model_name` for `from_state`, and add the missing simultaneous model+field rename test.
