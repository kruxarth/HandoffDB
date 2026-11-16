# Handoff: Missing `models` import in generated migrations

**Issue:** `makemigrations` emits `bases=(app.models.MyMixin, models.Model)` without importing `models`, producing a `NameError` at import time.

**Root cause (located):** `django/db/migrations/serializer.py`, `TypeSerializer.serialize()` (lines 273–287). The `special_cases` table (lines 275–278) maps `models.Model` to the string `"models.Model"` with an **empty imports set** (`[]`). So the literal `models.Model` is written but no `from django.db import models` is registered. Other serializers (`DeconstructableSerializer._serialize_path`, lines 94–102) correctly add that import for `django.db.models.*` paths, which is why fields like `app.models.MyField` work — but bases rendered via `TypeSerializer` are not covered. Note `models.Model` is the default base (`CreateModel.__init__`, `django/db/migrations/operations/models.py:49`), so it appears in the `bases` kwarg whenever a user mixes in a non-model base (as in `MyMixin`), matching the report.

**Related code:** `django/db/migrations/writer.py` lines 156–171 dedupe/merge imports; it only folds `from django.db import models` into `migrations, models` when that import was already present, so it cannot compensate for the missing entry. `django/db/migrations/state.py` lines 676–703 (`flatten_bases`) determines which bases survive into the operation.

**Tests:** `tests/migrations/test_writer.py` — `test_simple_migration` (~line 661) uses `(models.Model,)` as bases but doesn't assert the import; `serialize_round_trip`/`safe_exec` helpers at lines 202–228 are the right place to add a regression test asserting `from django.db import models` is emitted for a `CreateModel` whose bases include `models.Model`.

**Docs:** `docs/topics/migrations.txt` (writer/serializer behavior) — no change needed.

**Ruled out:** `writer.py` import-merging logic and `state.py` base flattening are behaving as designed; the bug is purely the empty import set in `TypeSerializer`.

**Conclusion:** Add `"from django.db import models"` to the `models.Model` special case in `TypeSerializer`.
