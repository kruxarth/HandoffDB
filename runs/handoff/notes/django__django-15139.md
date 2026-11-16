## Handoff: Deprecate `PickleSerializer` (move out of core)

**Issue:** Pickle is RCE-prone; deprecate `PickleSerializer` and move it out of `django.core`.

**Code that matters**
- `django/core/serializers/base.py:10-25` — `PickleSerializer` class (protocol/dumps/loads) is the public-but-undocumented target.
- `django/contrib/sessions/serializers.py:1-7` — imports it as `BasePickleSerializer` and re-exports `PickleSerializer`; the sessions copy must keep working (with deprecation warning) because `SESSION_SERIALIZER` accepts the dotted path.
- `django/core/cache/backends/redis.py:7,12` — `RedisSerializer(PickleSerializer)`; needs its own pickle implementation once the base class moves.
- `django/__init__.py` — version is `4.1.0 alpha 0`, so deprecation lands in 4.1.

**Ruled out:** `django/core/cache/backends/{db,filebased,locmem}.py` and `django/core/signing.py` use `pickle` directly, not `PickleSerializer`; no other core importers exist. `grep` confirmed only sessions, redis, and tests reference the class.

**Tests**
- `tests/serializers/tests.py:9,422-432` — `PickleSerializerTests` (protocol, dumps/loads); move/retarget.
- `tests/sessions_tests/tests.py:28,337,889` — imports and `SESSION_SERIALIZER` override; add `assertWarns`/`ignore_warnings` for the deprecation.
- `tests/defer_regress/tests.py:94` — uses the string path; ensure it still resolves.
- `tests/cache/tests.py:1666-1684` — Redis backend coverage (only runs when Redis configured).

**Docs**
- `docs/topics/http/sessions.txt:127,264,361-372,671` — warnings/class docs.
- `docs/ref/settings.txt:3389-3394` — `SESSION_SERIALIZER` values.
- `docs/releases/4.1.txt:350+` — "Features deprecated in 4.1".
- `docs/internals/deprecation.txt` — add removal entry (5.0/5.1 per policy).

**Conclusion:** Emit a `RemovedInDjango50Warning` from `PickleSerializer.__init__`, inline the pickle implementation into the sessions serializer and `RedisSerializer`, keep the core class importable until removal, and document the deprecation.
