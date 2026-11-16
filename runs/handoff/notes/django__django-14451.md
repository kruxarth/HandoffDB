## Handoff: self-closing tags in syndication feeds

**Issue:** Django’s syndication feeds never emit XML self-closing tags (`<tag/>`) for empty elements, even though Python’s `XMLGenerator` supports `short_empty_elements` (3.2+). `SimplerXMLGenerator` inherits directly from `XMLGenerator` and currently exposes no way to enable this.

**Key code:**
- `django/utils/xmlutils.py:13-33` — `SimplerXMLGenerator`. `addQuickElement()` (14-20) always calls `startElement()` then `endElement()`; with `short_empty_elements=True`, `endElement()` emits `/>` when no characters were written. `startElement()` (30-33) sorts attrs.
- `django/utils/feedgenerator.py:189-228` (`RssFeed.write`) and `298-358` (`Atom1Feed.write`) — instantiate `SimplerXMLGenerator(outfile, encoding)` at lines **190** and **299**. These are the syndication paths that should pass `short_empty_elements=True`.
- `django/core/serializers/xml_serializer.py:30` — also instantiates `SimplerXMLGenerator`; unrelated to syndication, so its output should not change.

**Tests/docs:** Low-level feed tests: `tests/utils_tests/test_feedgenerator.py`; high-level syndication tests: `tests/syndication_tests/tests.py` and `tests/syndication_tests/feeds.py`; geo feed tests: `tests/gis_tests/geoapp/test_feeds.py`. Docs: `docs/ref/utils.txt` (feedgenerator) and `docs/ref/contrib/syndication.txt`.

**Ruled out:** Changing `SimplerXMLGenerator`’s global default, because that would alter XML serializer output at `xml_serializer.py:30`. Also ruled out touching `addQuickElement()` logic itself; enabling the inherited `short_empty_elements` behavior is sufficient.

**Conclusion:** Add an `__init__` to `SimplerXMLGenerator` forwarding `short_empty_elements` with a backwards-compatible default (`False`), then pass `short_empty_elements=True` only at `feedgenerator.py:190` and `:299`. Add regression tests asserting empty RSS/Atom elements render as self-closing.
