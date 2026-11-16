## Handoff note

**Issue:** `UserCreationForm.save(commit=True)` does not persist data for `ManyToManyField`s on custom user models because it overrides `ModelForm.save()` and never calls `self.save_m2m()`.

**Key code:** `django/contrib/auth/forms.py`
- `UserCreationForm` starts at line 84.
- Its overridden `save()` is at line 139. It calls `super().save(commit=False)`, sets the password, saves the user when `commit=True`, and returns without `save_m2m()`. This is the defect.
- `UserChangeForm` starts at line 147; its `save()` is at line 309. It should be checked while implementing, but the reported issue is specifically `UserCreationForm`.

**Tests/models:**
- `tests/auth_tests/test_forms.py`: `UserCreationFormTest` begins at line 56; add a regression test there.
- `tests/auth_tests/models/with_many_to_many.py` already defines a custom user model with M2M fields, suitable for the test.
- Related docs: `docs/ref/contrib/auth.txt` and `docs/topics/auth/customizing.txt` cover `UserCreationForm` and custom user models.

**Ruled out:** The bug is not in `ModelForm` or form-field handling; `ModelForm.save()` already supports M2M saving. It is isolated to the auth form’s overridden `save()` path. No view/admin change is needed.

**Conclusion:** Confirmed. Fix `UserCreationForm.save()` so that when `commit=True`, after `user.save()`, it calls `self.save_m2m()`. Add a regression test using the M2M custom user model and verify the selected related objects are saved.
