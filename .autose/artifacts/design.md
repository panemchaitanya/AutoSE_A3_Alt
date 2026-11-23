# Design: String Document IDs in Update and Remove Operations

## Approach
To ensure `update()` and `remove()` accept string document IDs (such as `'1'`) consistently with `get(doc_ids=...)`, we need to normalize any provided `doc_ids` into the table's document ID class (`self.document_id_class`, defaulting to `int`) before checking existence or mutating the table. In `Table.update()` and `Table.remove()`, `doc_ids` is currently processed directly as an iterable of whatever types are passed, meaning string IDs like `'1'` fail to match integer keys in the `table` dictionary. Converting each `doc_id` in `doc_ids` using `self.document_id_class(doc_id)` (or supporting any custom document ID class/type coercion) will align `update()` and `remove()` with how `get()` and table storage handling work.

## Files to change
- `tinydb/table.py`
- `tests/test_tinydb.py` (NEW or existing test file where table unit tests reside)

## Functions/classes
- `Table.update`: Modify the handling of `doc_ids` to normalize each requested ID via `self.document_id_class(doc_id)`. Also update type hints if appropriate.
- `Table.remove`: Modify the handling of `doc_ids` to normalize each requested ID via `self.document_id_class(doc_id)`. Also update type hints if appropriate.

## Test plan
- Test `db.update({'x': 2}, doc_ids=['1'])` on a database with integer ID `1`, asserting the document is updated and `[1]` is returned.
- Test `db.remove(doc_ids=['1'])` on a database with integer ID `1`, asserting the document is removed and `[1]` is returned.
- Test with mixed string/integer IDs and non-existent IDs to ensure backward compatibility and robust error handling/silently skipping.

## Constraints respected
- ADR 1 / ADR 4 / Layering constraints: The mutation methods continue to follow the correct storage round-trip and query cache clearing behaviors via `_update_table`.
