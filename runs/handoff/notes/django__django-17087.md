# Handoff: classmethod default from nested class serializes wrong path

**Issue:** A `@classmethod` defined on a nested class (e.g. `Profile.Capability.default`) used as a `Field.default` serializes as `appname.models.Capability.default` instead of `appname.models.Profile.Capability.default`, breaking the migration.

**Key file:** `django/db/migrations/serializer.py`

- `FunctionTypeSerializer` (lines 164–189). Line 171 builds the path for methods bound to a class: `"%s.%s.%s" % (module, klass.__name__, self.value.__name__)`. Using `klass.__name__` drops the enclosing class, causing the bug. Change to `klass.__qualname__`.
- Lines 182–183 already use `self.value.__qualname__` for the unbound fallback (handles `<locals>`), confirming qualname is the right accessor.
- `TypeSerializer` (lines 308–326) already uses `self.value.__qualname__` at line 322 — the fix aligns with existing behavior.
- `EnumSerializer`/`ChoicesSerializer` (lines 59–63, 129–150) already emit correct nested paths, so they are not implicated.

**Tests:** `tests/migrations/test_writer.py` — `test_serialize_nested_class` (lines 459–464) covers nested enum/choices only. Add a regression test there for a nested-class classmethod default (e.g. a model with an inner class holding a classmethod returning a list), asserting `appname.models.Outer.Inner.default` in output.

**Docs:** No dedicated serializer docs; migration behavior is documented in `docs/topics/migrations.txt`. A release note under `docs/releases/` may be warranted depending on policy.

**Ruled out:** DeconstructableSerializer path serialization (lines 86–113), function qualname fallback (lines 182–188), and enum/choices serializers — all already handle nesting correctly.

**Conclusion:** One-line fix at `serializer.py:171` (`klass.__name__` → `klass.__qualname__`) plus a regression test in `tests/migrations/test_writer.py` near line 459.
