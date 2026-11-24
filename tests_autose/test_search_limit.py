import pytest
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage

@pytest.fixture
def db():
    db = TinyDB(storage=MemoryStorage)
    table = db.table('test')
    for i in range(1, 101):
        table.insert({'val': 1, 'id': i})
    return table

def test_ac_001_1(db):
    """Given a table containing 100 documents matching a condition, when db.search(cond, limit=10) is invoked, then exactly 10 documents are returned in ascending document ID order."""
    cond = Query().val == 1
    results = db.search(cond, limit=10)
    assert len(results) == 10
    # Verify ascending order by checking doc_id
    ids = [r.doc_id for r in results]
    assert ids == sorted(ids)
    assert ids == list(range(1, 11))

def test_ac_001_2(db):
    """Given a table containing matching documents, when db.search(cond) or db.search(cond, limit=None) is invoked, then all matching documents are returned in ascending document ID order."""
    cond = Query().val == 1
    results_default = db.search(cond)
    results_none = db.search(cond, limit=None)
    assert len(results_default) == 100
    assert len(results_none) == 100
    ids = [r.doc_id for r in results_default]
    assert ids == list(range(1, 101))

def test_ac_001_3(db):
    """Given a table containing 5 documents matching a condition, when db.search(cond, limit=10) is invoked, then all 5 documents are returned."""
    # Create a table with only 5 matches
    db2 = TinyDB(storage=MemoryStorage)
    table = db2.table('small')
    for i in range(1, 6):
        table.insert({'val': 2})
    
    results = table.search(Query().val == 2, limit=10)
    assert len(results) == 5