from tinydb import where, TinyDB
from tinydb.storages import MemoryStorage
from tinydb.operations import increment, add, subtract
import pytest

@pytest.fixture
def db():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'a'})
    return db

def test_increment_missing(db):
    db.update(increment('count'), where('name') == 'a')
    assert db.get(where('name') == 'a')['count'] == 1

def test_add_missing(db):
    db.update(add('count', 5), where('name') == 'a')
    assert db.get(where('name') == 'a')['count'] == 5

def test_subtract_missing(db):
    db.update(subtract('count', 3), where('name') == 'a')
    assert db.get(where('name') == 'a')['count'] == -3
