# Spec: Consistent Document ID Handling in update() and remove()

## Source
Issue title: "update() and remove() silently do nothing when I pass the doc id as a string"
Quoted key sentences: 
- "`db.get(doc_id='1')` finds my document fine, but when I pass the same id as a string to `update` or `remove`, nothing happens."
- "Passing the int `1` instead of `'1'` works. My ids come from a web form so they are always strings... Please make these consistent with `get` (which accepts the string form)."

## Requirements
- FR-1: The table `update` method shall accept document IDs passed as string representations of integers (e.g., `'1'`), converting them appropriately or matching them against integer document IDs consistently with `get()`.
- FR-2: The table `remove` method shall accept document IDs passed as string representations of integers (e.g., `'1'`), converting them appropriately or matching them against integer document IDs consistently with `get()`.
- FR-3: Database and Table proxy methods (`Database.update`, `Database.remove`, etc.) wrapping table operations shall maintain this consistent ID handling.

## Acceptance criteria
- AC-001-1: Given a database containing a document inserted with default integer ID 1, when `db.update({'x': 2}, doc_ids=['1'])` is invoked, then the document with ID 1 is updated to `{'x': 2}` and the method returns `[1]` (or the updated document IDs list, consistent with integer ID list updates).
- AC-002-1: Given a database containing a document inserted with default integer ID 1, when `db.remove(doc_ids=['1'])` is invoked, then the document with ID 1 is removed from the table and the method returns `[1]` (or the removed document IDs list).
- AC-003-1: Given a database containing a document inserted with default integer ID 1, when `db.get(doc_id='1')` is invoked, it returns the document (confirming baseline consistency).

## Assumptions and open questions
- ASM-1: String IDs representing integers should be coerced/converted to integers when matching document IDs, since TinyDB document IDs are integer-based by default. (Chosen default based on user request to be consistent with `get()`).
- ASM-2: Invalid non-integer strings (e.g., `'abc'`) should continue to not match any document IDs without raising an unexpected exception, or behave consistently with existing type handling for non-existent/invalid IDs.
