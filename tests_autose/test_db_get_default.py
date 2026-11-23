import pytest
from tinydb import TinyDB, Query, where

def test_get_doc_id_default(db: TinyDB):
    """Given a database without a document matching doc_id=42, when db.get(doc_id=42, default={}) is invoked, then the return value is {}."""
    db.drop_tables()
    assert db.get(doc_id=42, default={}) == {}

def test_get_query_default(db: TinyDB):
    """Given a database without a document matching query Query().name == 'x', when db.get(Query().name == 'x', default=[]) is invoked, then the return value is []."""
    db.drop_tables()
    assert db.get(Query().name == 'x', default=[]) == []

def test_get_doc_id_omitted_default(db: TinyDB):
    """Given a database without a document matching doc_id=42, when db.get(doc_id=42) is invoked without the default parameter, then the return value is None."""
    db.drop_tables()
    assert db.get(doc_id=42) is None

def test_get_doc_id_matched_with_default(db: TinyDB):
    """Given a database containing a document with doc_id=42, when db.get(doc_id=42, default={}) is invoked, then the return value is the matched document dictionary."""
    db.drop_tables()
    db.insert({'name': 'test'}) # gets doc_id 1
    # insert with specific doc_id if possible or use whatever gets inserted
    doc_id = db.insert({'name': 'target'}, doc_id=42)
    res = db.get(doc_id=42, default={})
    assert res == {'name': 'target'}
    assert res.doc_id == 42
