import sys
from utils import scrape_all_pdfs_recursive



class FakeConn:
    def __init__(self, response_map=None):
        self.row_factory = None
        self._response_map = response_map or {}
        self._last_query = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, *a, **k):
        if a:
            self._last_query = str(a[0])
        return self

    def fetchall(self):
        if self._last_query and "sqlite_master" in self._last_query:
            return []
        return []

    def fetchone(self):
        if not self._last_query:
            return (0,)
        for key, value in self._response_map.items():
            if key in self._last_query:
                return value
        return (0,)

    def executescript(self, script):
        pass

    def commit(self):
        pass

    def close(self):
        pass

    def cursor(self):
        return self




def fake_connect(*a, **kw):
    return FakeConn()

def test_main_no_pdfs_found(monkeypatch, tmp_path, capsys):
    # Patch sys.argv to simulate CLI call
    test_args = ["prog", "--root-dirs", str(tmp_path), "--domain", "testdomain", "--output-db", str(tmp_path/"test.sqlite"), "--workers", "1"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Patch find_all_pdfs to return empty list
    monkeypatch.setattr(scrape_all_pdfs_recursive, "find_all_pdfs", lambda dirs: [])

    # Patch input to avoid blocking
    monkeypatch.setattr("builtins.input", lambda _: "n")

    # Patch sqlite3.connect to avoid real DB work
    monkeypatch.setattr(scrape_all_pdfs_recursive.sqlite3, "connect", lambda *a, **kw: FakeConn())

    # Run main and capture output
    scrape_all_pdfs_recursive.main()
    out = capsys.readouterr().out
    assert "No PDFs found" in out


# Additional tests to cover more branches in main()
def test_main_user_cancels(monkeypatch, tmp_path, capsys):
    # Simulate finding PDFs but user cancels at prompt
    test_args = ["prog", "--root-dirs", str(tmp_path), "--domain", "testdomain", "--output-db", str(tmp_path/"test.sqlite"), "--workers", "1"]
    monkeypatch.setattr(sys, "argv", test_args)
    monkeypatch.setattr(scrape_all_pdfs_recursive, "find_all_pdfs", lambda dirs: [tmp_path/"a.pdf"])
    monkeypatch.setattr("builtins.input", lambda _: "n")
    monkeypatch.setattr(scrape_all_pdfs_recursive.sqlite3, "connect", lambda *a, **kw: FakeConn())
    scrape_all_pdfs_recursive.main()
    out = capsys.readouterr().out
    assert "Cancelled" in out


def test_main_db_init(monkeypatch, tmp_path, capsys):
    # Simulate DB does not exist, schema file missing
    test_args = ["prog", "--root-dirs", str(tmp_path), "--domain", "testdomain", "--output-db", str(tmp_path/"test.sqlite"), "--workers", "1"]
    monkeypatch.setattr(sys, "argv", test_args)
    monkeypatch.setattr(scrape_all_pdfs_recursive, "find_all_pdfs", lambda dirs: [tmp_path/"a.pdf"])
    monkeypatch.setattr("builtins.input", lambda _: "y")
    monkeypatch.setattr(scrape_all_pdfs_recursive.Path, "exists", lambda self: False)
    monkeypatch.setattr(scrape_all_pdfs_recursive.Path, "read_text", lambda self, encoding=None: "" if "schema" in str(self) else "file contents")
    monkeypatch.setattr(scrape_all_pdfs_recursive.sqlite3, "connect", fake_connect)
    # Patch Pool to a dummy context manager that runs sequentially
    class DummyPool:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def imap_unordered(self, func, iterable):
            return map(func, iterable)
    monkeypatch.setattr(scrape_all_pdfs_recursive, "Pool", DummyPool)
    scrape_all_pdfs_recursive.main()
    out = capsys.readouterr().out
    assert "Schema file not found" in out or "Initializing database schema" in out


def test_find_all_pdfs_dir_not_found(monkeypatch, tmp_path, capsys):
    import pathlib
    PathBase = type(pathlib.Path())
    class PathStub(PathBase):
        def exists(self):
            return False
    monkeypatch.setattr(scrape_all_pdfs_recursive, "Path", PathStub)
    out = scrape_all_pdfs_recursive.find_all_pdfs([tmp_path/"missingdir"])
    assert out == []


def test_main_parallel_and_db_stats(monkeypatch, tmp_path, capsys):
    # Simulate all major branches: parallel scrape, failed PDFs, DB stats
    test_args = ["prog", "--root-dirs", str(tmp_path), "--domain", "testdomain", "--output-db", str(tmp_path/"test.sqlite"), "--workers", "1"]
    monkeypatch.setattr(sys, "argv", test_args)
    # Patch find_all_pdfs to return PDFs
    monkeypatch.setattr(scrape_all_pdfs_recursive, "find_all_pdfs", lambda dirs: [tmp_path/"a.pdf", tmp_path/"b.pdf"])
    # Patch input to 'y'
    monkeypatch.setattr("builtins.input", lambda _: "y")
    # Patch DB path exists using PathStub
    import pathlib
    PathBase = type(pathlib.Path())
    class PathStub(PathBase):
        def exists(self):
            return True
    monkeypatch.setattr(scrape_all_pdfs_recursive, "Path", PathStub)
    # Patch sqlite3.connect to simulate DB stats using the shared FakeCon
    response_map = {
        "COUNT(*) FROM research_events": (42,),
        "COUNT(DISTINCT entity_id) FROM entities": (7,),
        "COUNT(DISTINCT source_id) FROM sources": (3,)
    }
    monkeypatch.setattr(scrape_all_pdfs_recursive.sqlite3, "connect", lambda *a, **kw: FakeConn(response_map=response_map))
    # Patch Pool and tqdm to avoid real parallelism
    class FakePool:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def imap_unordered(self, func, args):
            return iter([
                ("a.pdf", 10, True, None),
                ("b.pdf", 0, False, "fail")
            ])
    monkeypatch.setattr(scrape_all_pdfs_recursive, "Pool", lambda processes: FakePool())
    monkeypatch.setattr(scrape_all_pdfs_recursive, "tqdm", lambda x, **kw: x)
    scrape_all_pdfs_recursive.main()
    out = capsys.readouterr().out
    assert "SCRAPING COMPLETE" in out
    assert "Failed PDFs" in out
    assert "DATABASE STATISTICS" in out
    assert "Total events in database: 42" in out
    assert "Total unique entities: 7" in out
    assert "Total papers: 3" in out
