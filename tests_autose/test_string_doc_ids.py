import pytest
from tinydb import TinyDB
from tinydb.storages import MemoryStorage


def test_update_with_string_doc_id():
    """AC-001-1: Given a database containing a document with integer ID 1, when db.update({'x': 2}, doc_ids=['1']) is executed, then the document with ID 1 is updated to {'x': 2} and the method returns [1]."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'x': 1})
    
    result = db.update({'x': 2}, doc_ids=['1'])
    assert result == [1]
    assert db.get(doc_id=1) == {'x': 2}


def test_remove_with_string_doc_id():
    """AC-002-1: Given a database containing a document with integer ID 1, when db.remove(doc_ids=['1']) is executed, then the document with ID 1 is removed from the database and the method returns [1]."""
    db = TinyDB(storage=MemoryStorage)
    db.insert({'x': 1})
    
    result = db.remove(doc_ids=['1'])
    assert result == [1]
    assert len(db) == 0
