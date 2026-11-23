# Spec: Add default value parameter to db.get()

## Source
Issue #4: "Let get() take a default value, like dict.get"
Quotes: 
- "db.get(...) returns None when nothing matches."
- "It would be cleaner if get accepted a default, the way dict.get does: db.get(doc_id=42, default={}), db.get(Query().name == 'x', default={})"
- "Behavior when the call does match should be exactly what it is today, and omitting default should keep returning None."

## Requirements
- FR-1: The database get method shall accept an optional keyword argument named `default` for single-document queries (by `doc_id` or query condition).
- FR-2: When a single-document query matches no document and a `default` value is provided, `db.get()` shall return the specified `default` value instead of `None`.
- FR-3: When a single-document query matches no document and the `default` argument is omitted, `db.get()` shall return `None` (preserving existing behavior).
- FR-4: When a single-document query matches a document, `db.get()` shall return the matched document regardless of whether `default` is provided or what value it holds (preserving existing matched behavior).

## Acceptance criteria
- Given a database without a document matching `doc_id=42`, when `db.get(doc_id=42, default={})` is invoked, then the return value is `{}`.
- Given a database without a document matching query `Query().name == 'x'`, when `db.get(Query().name == 'x', default=[])` is invoked, then the return value is `[]`.
- Given a database without a document matching `doc_id=42`, when `db.get(doc_id=42)` is invoked without the `default` parameter, then the return value is `None`.
- Given a database containing a document with `doc_id=42`, when `db.get(doc_id=42, default={})` is invoked, then the return value is the matched document dictionary.

## Assumptions and open questions
- Assumption: The `default` parameter is strictly a keyword-only or keyword argument (`default=...`), aligning with python's typical configuration for optional fallback values and explicit usage shown in the issue examples (`db.get(doc_id=42, default={})`).
