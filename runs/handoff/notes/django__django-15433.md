**Handoff note**

Issue: `ManyToManyField(settings.AUTH_USER_MODEL)` on a custom user extending `AbstractUser` generates repeated identical `AlterField` migrations when the swappable setting is lowercased.

Key code:
- `django/db/models/fields/related.py`, `ManyToManyField.deconstruct()` around lines 1727–1745. At line 1735 it serializes `kwargs["to"] = self.remote_field.model._meta.label`, preserving case, so the deconstructed field differs from the lowercased migration state and triggers endless `AlterField`.
- Compare `ForeignKey.deconstruct()` in the same file, lines 671–702, especially 679–686 (`_meta.label_lower`) and 689–702 (swappable setting handling). `ForeignKey` normalizes to lowercase and handles swappable settings; `ManyToManyField` does not.
- `django/apps/registry.py`, `get_swappable_settings_name()` lines 283–295, lowercases `to_string`; this explains why lowercase swappable settings expose the mismatch.

Tests:
- `tests/migrations/test_autodetector.py`: `test_swappable` at 3241, `test_swappable_lowercase` at 3255. Add/adjust a regression test here for a lowercased `AUTH_USER_MODEL` plus `ManyToManyField`.
- Related swappable state coverage: `tests/migrations/test_state.py` around 1730–1827; writer coverage: `tests/migrations/test_writer.py` around 582.

Ruled out: the autodetector comparison itself (`deep_deconstruct`, `generate_altered_fields`), migration state cloning/`from_model`, and the swappable-name cache. The registry correctly lowercases; the M2M field deconstruction is the asymmetry.

Conclusion: fix `ManyToManyField.deconstruct()` to use `_meta.label_lower` and mirror `ForeignKey`’s swappable-setting normalization. Docs are contextual only (migration/field reference); no doc change required.
