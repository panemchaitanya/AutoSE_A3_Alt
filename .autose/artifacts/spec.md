# Spec: Deep copy or isolation of search and retrieval results to prevent in-place mutation side effects

## Source
Issue #5: "Searches sometimes return data that doesn't match what's in the db??"
Quotes:
- "Sometimes a search returns documents with values that are NOT what's stored."
- "I search for something, tweak the returned dicts a bit for display purposes (like formatting a field), and later when I run the SAME search again the old tweaked values show up even though I never called update or anything."
- "It's like tinydb remembers my display edits."
- "If I restart the script the data is fine again, so the file itself is OK. It only happens within one run and only sometimes (maybe only when I edit the dicts I got back?). Is this a caching bug? Can you make it so the documents you get back from search/all are just... normal dicts you can safely edit without side effects?"

## Requirements
- FR-1: The storage or query engine shall return deep copies (or fully isolated instances) of stored documents upon search, retrieval, or iteration (`all()`) such that subsequent in-place modifications to the returned dictionary objects do not affect cached instances or subsequent search results within the same runtime execution. [Stated/Inferred]
- NFR-1: The retrieval isolation mechanism shall not introduce a regression in search or document retrieval latency exceeding TBD% overhead compared to current direct reference returns. [Assumed]

## Acceptance criteria
- AC-1-1: Given a document stored in the database, When a user executes a search or retrieves all documents, modifies a nested value or field on the returned dictionary in-place, and subsequently executes the exact same search or retrieval operation again within the same Python process, Then the returned dictionary reflects the original stored database state rather than the modified display values.
- AC-1-2: Given a document stored in the database, When a user retrieves documents and modifies the returned dictionary objects, Then the underlying database cache or internal storage structures remain unmutated.

## Assumptions and open questions
- ASM-1: Deep copying is the intended solution to prevent in-place mutation side effects as requested by the user, assuming acceptable performance impact. [Default chosen to address user request directly]
- Q-1: Should document isolation be performed via `copy.deepcopy` or an alternative serialization/deserialization approach, and what is the exact performance tolerance for large datasets?