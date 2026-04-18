import sys
import types
from utils import scrape_all_pdfs_recursive

def test_main_no_pdfs_found(monkeypatch, tmp_path, capsys):
    # Patch sys.argv to simulate CLI call
    test_args = ["prog", "--root-dirs", str(tmp_path), "--domain", "testdomain", "--output-db", str(tmp_path/"test.sqlite"), "--workers", "1"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Patch find_all_pdfs to return empty list
    monkeypatch.setattr(scrape_all_pdfs_recursive, "find_all_pdfs", lambda dirs: [])

    # Patch input to avoid blocking
    monkeypatch.setattr("builtins.input", lambda _: "n")

    # Patch sqlite3.connect to avoid real DB work
    monkeypatch.setattr(scrape_all_pdfs_recursive.sqlite3, "connect", lambda *a, **kw: types.SimpleNamespace(__enter__=lambda s: s, __exit__=lambda s, exc_type, exc_val, exc_tb: None, execute=lambda *a, **k: [], commit=lambda: None, close=lambda: None, row_factory=None, cursor=lambda self: self))

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
    monkeypatch.setattr(scrape_all_pdfs_recursive.sqlite3, "connect", lambda *a, **kw: types.SimpleNamespace(__enter__=lambda s: s, __exit__=lambda s, exc_type, exc_val, exc_tb: None, execute=lambda *a, **k: [], commit=lambda: None, close=lambda: None, row_factory=None, cursor=lambda self: self))
    scrape_all_pdfs_recursive.main()
    out = capsys.readouterr().out
    assert "Cancelled" in out


def test_main_db_init(monkeypatch, tmp_path, capsys):
    # Simulate DB does not exist, schema file missing
    test_args = ["prog", "--root-dirs", str(tmp_path), "--domain", "testdomain", "--output-db", str(tmp_path/"test.sqlite"), "--workers", "1"]
    monkeypatch.setattr(sys, "argv", test_args)
    monkeypatch.setattr(scrape_all_pdfs_recursive, "find_all_pdfs", lambda dirs: [tmp_path/"a.pdf"])
    monkeypatch.setattr("builtins.input", lambda _: "y")
    # Patch DB path to not exist
    monkeypatch.setattr(scrape_all_pdfs_recursive.Path, "exists", lambda self: False)
    # Patch schema path to not exist
    monkeypatch.setattr(scrape_all_pdfs_recursive.Path, "read_text", lambda self, encoding=None: "")
    monkeypatch.setattr(scrape_all_pdfs_recursive.sqlite3, "connect", lambda *a, **kw: types.SimpleNamespace(__enter__=lambda s: s, __exit__=lambda s, exc_type, exc_val, exc_tb: None, execute=lambda *a, **k: [], commit=lambda: None, close=lambda: None, row_factory=None, cursor=lambda self: self))
    scrape_all_pdfs_recursive.main()
    out = capsys.readouterr().out
    assert "Schema file not found" in out or "Initializing database schema" in out


def test_find_all_pdfs_dir_not_found(monkeypatch, tmp_path, capsys):
    # Patch Path.exists to always return False
    monkeypatch.setattr(scrape_all_pdfs_recursive.Path, "exists", lambda self: False)
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
    # Patch DB path exists
    monkeypatch.setattr(scrape_all_pdfs_recursive.Path, "exists", lambda self: True)
    # Patch sqlite3.connect to simulate DB stats
    class FakeCon:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def execute(self, q):
            self._last_query = q
            return self
        def fetchone(self):
            if "COUNT(*) FROM research_events" in getattr(self, '_last_query', ''):
                return (42,)
            if "COUNT(DISTINCT entity_id) FROM entities" in getattr(self, '_last_query', ''):
                return (7,)
            if "COUNT(DISTINCT source_id) FROM sources" in getattr(self, '_last_query', ''):
                return (3,)
            return (0,)
        def fetchall(self): return [("table1",), ("table2",)]
        def commit(self): pass
        def close(self): pass
        def executescript(self, script): pass
        @property
        def row_factory(self): return None
        @row_factory.setter
        def row_factory(self, v): pass
        def cursor(self): return self
    monkeypatch.setattr(scrape_all_pdfs_recursive.sqlite3, "connect", lambda *a, **kw: FakeCon())
    # Patch Pool and tqdm to avoid real parallelism
    class FakePool:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def imap_unordered(self, func, args):
            return iter([["a.pdf", 10, True, None], ["b.pdf", 0, False, "fail"]])
    monkeypatch.setattr(scrape_all_pdfs_recursive, "Pool", lambda processes: FakePool())
    monkeypatch.setattr(scrape_all_pdfs_recursive, "tqdm", lambda x, **kw: x)
    # Patch process_single_pdf
    monkeypatch.setattr(scrape_all_pdfs_recursive, "process_single_pdf", lambda args: (args[0], 10, True, None))
    scrape_all_pdfs_recursive.main()
    out = capsys.readouterr().out
    assert "SCRAPING COMPLETE" in out
    assert "Failed PDFs" in out
    assert "DATABASE STATISTICS" in out
    assert "Total events in database: 42" in out
    assert "Total unique entities: 7" in out
    assert "Total papers: 3" in out
