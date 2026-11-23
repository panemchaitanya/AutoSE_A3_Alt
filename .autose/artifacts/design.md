# Design: Add default value parameter to db.get()

## Approach
We will update `Table.get` in `tinydb/table.py` to support an optional keyword argument `default=None`. When a single-document query (either via `doc_id` or query condition `cond`) finds no matching document, it will return the provided `default` value instead of `None`. If `default` is omitted, it defaults to `None`, preserving existing behavior. When a match is found, the matched document is returned as before. We will also update overloads and typing as appropriate.

## Files to change
- `tinydb/table.py`
- `tinydb/database.py` (if database forwards get, let's check database.py first, or verify if database.py forwards methods)

## Functions/classes
- `Table.get`: add `default: Any = None` parameter, update return logic for single-document queries.
- `TinyDB` methods forwarding to default table: `TinyDB.get` needs to accept and forward `default` if it forwards `get`.

## Test plan
- Test `db.get(doc_id=42, default={})` returns `{}` when missing.
- Test `db.get(Query().name == 'x', default=[])` returns `[]` when missing.
- Test `db.get(doc_id=42)` returns `None` when missing (omitting `default`).
- Test `db.get(doc_id=42, default={})` returns the actual matched document when it exists.
- Test `db.get(Query().name == 'x', default={})` returns the actual matched document when it exists.

## Constraints respected
- Query cache handling and layering rules remain fully intact.
- Backward compatibility is preserved by defaulting `default=None`.