# Spec: Prevent mutating search and retrieval results from modifying internal database cache

## Source
- GitHub Issue #5: "Searches sometimes return data that doesn't match what's in the db??"
- Quoted key sentences:
  - S-01: "Sometimes a search returns documents with values that are NOT what's stored."
  - S-02: "Example: I search for something, tweak the returned dicts a bit for display purposes (like formatting a field), and later when I run the SAME search again the old tweaked values show up even though I never called update or anything."
  - S-03: "It's like tinydb remembers my display edits."
  - S-04: "If I restart the script the data is fine again, so the file itself is OK."
  - S-05: "It only happens within one run and only sometimes (maybe only when I edit the dicts I got back?)."
  - S-06: "Is this a caching bug? Can you make it so the documents you get back from search/all are just... normal dicts you can safely edit without side effects?"

## Requirements
- FR-001: The database search and retrieval methods (including document access, iteration, and search queries) shall return deep copies of the stored document dictionaries such that subsequent in-place mutations of the returned dictionaries by client code do not affect the internal database state or subsequent search/retrieval results.

## Acceptance criteria
- Given a document stored in the database, when the document is retrieved via search or table iteration, and the returned dictionary is modified in-place by client code, then executing the same search or retrieval again shall return the original un-mutated values stored in the database.

## Assumptions and open questions
- ASM-001: Deep copying documents upon retrieval or search return will not introduce prohibitive performance degradation for standard TinyDB usage. (Default chosen to ensure correctness and prevent side effects as requested).
