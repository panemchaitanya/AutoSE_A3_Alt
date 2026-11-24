# SRS: TinyDB Increment Operations Missing Field Handling (v1)

## 1. Purpose and scope

- S-01: "I'm using `tinydb.operations.increment` for a page-view counter. The first time a page is viewed the document has no `count` field yet, and instead of just starting the counter at 1, TinyDB blows up: KeyError: 'count'"
- S-02: "I would expect a counter on a missing field to simply start from 0, i.e. after the call above the document should be `{'page': '/home', 'count': 1}`. Same goes for `add` and `subtract`: adding 5 to a missing field should give 5, subtracting 3 should give -3."

## 2. Actors
| ID | Actor | Basis | Source |
|---|---|---|---|
| ACT-1 | Python Developer / TinyDB User | STATED | S-01, S-02 |

## 3. Constraints
| ID | Statement | Basis | Source | Gate |
|---|---|---|---|---|
| CON-1 | Must maintain compatibility with TinyDB 4 operations interface. | STATED | S-01 | READY |

## 4. Functional requirements
| ID | Statement | Basis | Source | Priority | Gate | AC |
|---|---|---|---|---|---|---|
| FR-001 | The `increment` operation shall initialize a missing field to 0 before incrementing by 1. | STATED | S-01, S-02 | MUST | READY | AC-001-1, AC-001-2 |
| FR-002 | The `decrement` operation shall initialize a missing field to 0 before decrementing by 1. | STATED | S-02 | MUST | READY | AC-002-1 |
| FR-003 | The `add` operation shall initialize a missing field to 0 before adding `n`. | STATED | S-02 | MUST | READY | AC-003-1, AC-003-2 |
| FR-004 | The `subtract` operation shall initialize a missing field to 0 before subtracting `n`. | STATED | S-02 | MUST | READY | AC-004-1 |

## 5. Non-functional reqs
| ID | Statement | Basis | Source | Priority | Gate | AC |
|---|---|---|---|---|---|---|
| NFR-001 | Execution time for `increment`, `decrement`, `add`, and `subtract` operations on a document with a missing field shall execute without raising `KeyError`. | STATED | S-01 | MUST | READY | AC-NFR-1 |

## 6. Acceptance criteria
| AC-id | Requirement | Criterion (given/when/then or measurable) |
|---|---|---|
| AC-001-1 | FR-001 | Given a document without the field 'count', when `db.update(increment('count'), doc_ids=[1])` is invoked, then the field 'count' is set to 1. |
| AC-001-2 | FR-001 | Given a document with existing 'count' equal to 5, when `db.update(increment('count'), doc_ids=[1])` is invoked, then 'count' becomes 6. |
| AC-002-1 | FR-002 | Given a document without the field 'count', when `db.update(decrement('count'), doc_ids=[1])` is invoked, then the field 'count' is set to -1. |
| AC-003-1 | FR-003 | Given a document without the field 'score', when `db.update(add('score', 5), doc_ids=[1])` is invoked, then the field 'score' is set to 5. |
| AC-003-2 | FR-003 | Given a document without the field 'str_field', when `db.update(add('str_field', 'abc'), doc_ids=[1])` is invoked, then the field 'str_field' is set to 'abc' (assuming 0 + string or handling appropriately per existing code). |
| AC-004-1 | FR-004 | Given a document without the field 'score', when `db.update(subtract('score', 3), doc_ids=[1])` is invoked, then the field 'score' is set to -3. |
| AC-NFR-1 | NFR-001 | Given any update operation using `increment`, `decrement`, `add`, or `subtract` on a missing field, no `KeyError` exception is raised and the update completes successfully. |

## 7. Dependencies and risks
| ID | Statement | Basis | Source |
|---|---|---|---|
| DEP-1 | TinyDB core library storage and document mapping. | STATED | S-01 |

## 8. Traceability
- S-01 -> FR-001, NFR-001
- S-02 -> FR-001, FR-002, FR-003, FR-004
- FR-001 -> S-01, S-02
- FR-002 -> S-02
- FR-003 -> S-02
- FR-004 -> S-02
- NFR-001 -> S-01
