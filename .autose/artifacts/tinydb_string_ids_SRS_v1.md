# SRS: TinyDB String Document IDs Support (v1)

## 1. Purpose and scope

This specification addresses the issue where `update()` and `remove()` methods in TinyDB silently do nothing when document IDs are passed as string representations of integers (e.g., `'1'`), whereas `db.get(doc_id='1')` correctly handles string IDs. 

Stated requirements derived directly from the user issue:
- S-01: `db.get(doc_id='1')` finds the document fine. [Stated in issue body]
- S-02: Passing the same id as a string to `update` or `remove` results in nothing happening (no error, no warning, document unchanged). [Stated in issue body]
- S-03: Passing the int `1` instead of `'1'` works. [Stated in issue body]
- S-04: User IDs come from a web form so they are always strings, and the user does not want to crash on every bad input, but a silent no-op on a write is the worst of both worlds. [Stated in issue body]
- S-05: Make these consistent with `get` (which accepts the string form). [Stated in issue body]

## 2. Actors

| ID | Actor | Basis | Source |
|---|---|---|---|
| ACT-1 | Developer / API Consumer | STATED | S-04 |

## 3. Constraints

| ID | Statement | Basis | Source | Gate |
|---|---|---|---|---|
| CON-1 | TinyDB 4.9.0, Python 3.12 environment | STATED | Issue body | READY |

## 4. Functional requirements

| ID | Statement | Basis | Source | Priority | Gate | AC |
|---|---|---|---|---|---|---|
| FR-001 | The `update` method shall accept document IDs passed as string representations of integers in `doc_ids` and successfully update the corresponding documents. | STATED | S-02, S-05 | MUST | READY | AC-001-1 |
| FR-002 | The `remove` method shall accept document IDs passed as string representations of integers in `doc_ids` and successfully remove the corresponding documents. | STATED | S-02, S-05 | MUST | READY | AC-002-1 |

## 5. Non-functional reqs

| ID | Statement | Basis | Source | Priority | Gate | AC |
|---|---|---|---|---|---|---|
| NFR-001 | Error handling consistency: write operations (`update`, `remove`) must behave consistently with read operations (`get`) regarding integer-convertible string document IDs without introducing silent no-ops. | STATED | S-05 | MUST | READY | AC-001-1, AC-002-1 |

## 6. Acceptance criteria

| AC-id | Requirement | Criterion (given/when/then or measurable) |
|---|---|---|
| AC-001-1 | FR-001 | Given a database containing a document with integer ID 1, when `db.update({'x': 2}, doc_ids=['1'])` is executed, then the document with ID 1 is updated to `{'x': 2}` and the method returns `[1]`. |
| AC-002-1 | FR-002 | Given a database containing a document with integer ID 1, when `db.remove(doc_ids=['1'])` is executed, then the document with ID 1 is removed from the database and the method returns `[1]`. |

## 7. Dependencies and risks

| ID | Statement | Basis | Source |
|---|---|---|---|
| RSK-1 | Converting or casting string IDs in `update` and `remove` might affect custom table storage or table queries if not implemented uniformly across ID lookups. | INFERRED | S-05 |

## 8. Traceability

- S-01 -> [FR-001, NFR-001]
- S-02 -> [FR-001, FR-002]
- S-03 -> [FR-001, FR-002]
- S-04 -> [ACT-1, NFR-001]
- S-05 -> [FR-001, FR-002, NFR-001]
- FR-001 -> [AC-001-1]
- FR-002 -> [AC-002-1]
- NFR-001 -> [AC-001-1, AC-002-1]
