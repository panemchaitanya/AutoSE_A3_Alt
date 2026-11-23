# Spec: String Document IDs in Update and Remove Operations

## Source
Issue title and body: "update() and remove() silently do nothing when I pass the doc id as a string"
Quotes: 
- "`db.get(doc_id='1')` finds my document fine, but when I pass the same id as a string to `update` or `remove`, nothing happens. No error, no warning, the document is just unchanged."
- "Please make these consistent with `get` (which accepts the string form)."

## Requirements
- FR-1: The `update()` method shall accept document IDs passed as strings (e.g., `'1'`), matching the behavior of `get()`, and successfully update the corresponding document(s).
- FR-2: The `remove()` method shall accept document IDs passed as strings (e.g., `'1'`), matching the behavior of `get()`, and successfully remove the corresponding document(s).

## Acceptance criteria
- AC-001-1: Given a database containing a document with integer ID `1`, when `db.update({'x': 2}, doc_ids=['1'])` is executed, then the document with ID `1` is updated to `{'x': 2}` and the method returns `[1]` (or the list of updated document IDs consistent with integer ID input behavior).
- AC-002-1: Given a database containing a document with integer ID `1`, when `db.remove(doc_ids=['1'])` is executed, then the document with ID `1` is removed from the database and the method returns `[1]` (or the list of removed document IDs consistent with integer ID input behavior).

## Assumptions and open questions
- ASM-1: String IDs representing integers (e.g. `'1'`) should be coerced or parsed to match integer document IDs if the underlying table storage uses integer keys, consistent with how `db.get(doc_id='1')` currently functions. (Default chosen because `get()` already accepts string IDs successfully without throwing an error).