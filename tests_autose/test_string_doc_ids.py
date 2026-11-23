from tinydb import TinyDB
from tinydb.storages import MemoryStorage

def test_update_accepts_string_doc_ids():
    """AC-001-1: Given a database containing a document with integer ID 1, when db.update({'x': 2}, doc_ids=['1']) is executed, then the document with ID 1 is updated to {'x': 2} and the method returns [1]."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'x': 1})
    # Document should have ID 1
    res = db.update({'x': 2}, doc_ids=['1'])
    assert res == [1]
    assert db.get(doc_id=1) == {'x': 2}

def test_remove_accepts_string_doc_ids():
    """AC-002-1: Given a database containing a document with integer ID 1, when db.remove(doc_ids=['1']) is executed, then the document with ID 1 is removed from the database and the method returns [1]."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'x': 1})
    # Document should have ID 1
    res = db.remove(doc_ids=['1'])
    assert res == [1]
    assert db.get(doc_id=1) is None
