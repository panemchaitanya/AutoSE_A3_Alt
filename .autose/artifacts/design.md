# Design: Deep copy or isolation of search and retrieval results to prevent in-place mutation side effects

## Approach
To prevent in-place mutation side effects on documents returned by search, retrieval, iteration, and get operations, we will ensure that every `Document` returned to the user is constructed from a deep copy (`copy.deepcopy`) of the stored document mapping. Specifically, in `Table.search`, `Table.get`, and `Table.__iter__` (which powers `Table.all`), we will wrap the document dictionary in `copy.deepcopy(...)` before passing it to `self.document_class`. Furthermore, cached search results in `Table.search` should return deep copies or be stored/retrieved such that mutations to previously returned search results do not affect future search results or the cache.

## Files to change
- `tinydb/table.py`
- `tests/test_tables.py` (NEW or modified to add test coverage for mutation side-effect prevention)

## Functions/classes
- Modify `Table.search` in `tinydb/table.py`
- Modify `Table.get` in `tinydb/table.py`
- Modify `Table.__iter__` in `tinydb/table.py`

## Test plan
- Test AC-1-1: Retrieve documents via `search`, `get`, and `all()`, mutate nested dictionaries/fields in-place, execute the same search/retrieval again, and verify that the returned documents reflect original database state rather than modified values.
- Test AC-1-2: Verify that mutating returned document dictionaries does not mutate the underlying storage cache or internal table states.

## Constraints respected
- ADR 1, ADR 2, ADR 3, and all architectural layering rules remain strictly respected.