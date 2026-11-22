# Spec: Fix update() and remove() with string document IDs

## Source
Issue #1: "update() and remove() silently do nothing when I pass the doc id as a string"
> "I spent an hour debugging this. `db.get(doc_id='1')` finds my document fine, but when I pass the same id as a string to `update` or `remove`, nothing happens. No error, no warning, the document is just unchanged. ... Please make these consistent with `get` (which accepts the string form)."

## Requirements

### FR-1: Update documents by string document IDs
- **Statement**: The table `update` method shall accept document IDs passed as strings in `doc_ids` and successfully update the corresponding documents.
- **Basis**: STATED
- **Source**: S-01
- **Priority**: MUST
- **Gate**: READY
- **AC**: AC-1-1

### FR-2: Remove documents by string document IDs
- **Statement**: The table `remove` method shall accept document IDs passed as strings in `doc_ids` and successfully remove the corresponding documents.
- **Basis**: STATED
- **Source**: S-02
- **Priority**: MUST
- **Gate**: READY
- **AC**: AC-2-1

## Acceptance criteria

- **AC-1-1**: Given a database containing a document with integer ID `1`, when `db.update({'x': 2}, doc_ids=['1'])` is executed, then the document is updated to `{'x': 2}` and `[1]` is returned.
- **AC-2-1**: Given a database containing a document with integer ID `1`, when `db.remove(doc_ids=['1'])` is executed, then the document is removed from the database and `[1]` is returned.

## Assumptions and open questions

- **ASM-1**: Document ID normalization should convert incoming `doc_ids` entries to match stored table keys so that string representations of integer IDs (e.g. `'1'`) match stored integer IDs (e.g. `1`), maintaining consistency with `get()` and `contains()`, and returning the stored integer IDs.
  - **Linked Q**: Q-1
- **Q-1**: Should `update()` and `remove()` return IDs in the format requested/stored or normalized? (Default chosen: return stored integer IDs `[1]` to match standard tinydb table return conventions when querying by integer IDs).