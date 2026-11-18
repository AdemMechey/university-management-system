import pytest, sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import database.db_setup as db_module

@pytest.fixture(autouse=True)
def use_test_db(monkeypatch):
    fd, test_db = tempfile.mkstemp(suffix=".db", dir=os.path.dirname(__file__))
    os.close(fd)
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    db_module.create_tables()
    yield test_db
    try:
        os.unlink(test_db)
    except OSError:
        pass
