# Register: TinyDB Increment Operations Missing Field Handling (v1)

## A. Source Statements
- S-01: "I'm using `tinydb.operations.increment` for a page-view counter. The first time a page is viewed the document has no `count` field yet, and instead of just starting the counter at 1, TinyDB blows up: KeyError: 'count'"
- S-02: "I would expect a counter on a missing field to simply start from 0, i.e. after the call above the document should be `{'page': '/home', 'count': 1}`. Same goes for `add` and `subtract`: adding 5 to a missing field should give 5, subtracting 3 should give -3."

## B. Ambiguous Terms
- None identified; requirements explicitly define behavior for missing fields based on user expectations.

## C. Open Questions
- None blocking.

## D. Assumptions
- None.

## E. Conflicts
- None.

## F. Evidence Log
- EV-1: A3 repository-local analysis of `tinydb/operations.py`, showing `add`, `subtract`, `increment`, and `decrement` already check `if field not in doc: doc[field] = 0` or similar for some operations, but `increment` and `decrement` previously threw `KeyError` before inspection / or need explicit confirmation against the issue description.

## G. Coverage Matrix
- Users and roles: COVERED (ACT-1)
- Core capabilities: COVERED (FR-001, FR-002, FR-003, FR-004)
- Data: COVERED
- Integrations: N/A
- Deployment and hosting: N/A
- Security and privacy: N/A
- Legal and compliance: N/A
- Performance and capacity: N/A
- Availability and recovery: N/A
- Observability and operations: N/A
- Usability and accessibility: N/A
- Maintainability and extensibility: N/A
- Autonomy and human oversight: N/A
- Success measures: COVERED (ACs)
- Scope exclusions: COVERED
- Delivery constraints: COVERED (CON-1)

## H. Change Log
- v1.0: Initial specification created from issue #2.
