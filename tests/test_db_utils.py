"""Tests for database utilities using pytest"""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from utils.db_utils import connect_db, get_tables, get_table_stats, inspect_database, show_recent_events, show_top_sources, get_entity_distribution, get_event_type_distribution, get_domain_distribution


class TestConnectDB:
    """Test database connection functionality"""
    
    def test_connect_db_valid_path(self):
        """Test connecting to a valid database"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            assert isinstance(conn, sqlite3.Connection)
            conn.close()
        finally:
            os.unlink(db_path)

    def test_connect_db_nonexistent_path(self):
        """Test connecting to a nonexistent database"""
        with pytest.raises(FileNotFoundError, match="Database not found"):
            connect_db('nonexistent_database.sqlite')

    def test_connect_db_invalid_path(self):
        """Test connecting with invalid path"""
        with pytest.raises(FileNotFoundError, match="Database not found"):
            connect_db('/invalid/path/database.sqlite')


class TestGetTables:
    """Test table listing functionality"""
    
    def test_get_tables_empty_database(self):
        """Test getting tables from empty database"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            tables = get_tables(conn)
            assert tables == []
            conn.close()
        finally:
            os.unlink(db_path)

    def test_get_tables_with_tables(self):
        """Test getting tables from database with tables"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            # Create test tables
            conn.execute("CREATE TABLE test_table1 (id INTEGER)")
            conn.execute("CREATE TABLE test_table2 (name TEXT)")
            conn.commit()
            
            tables = get_tables(conn)
            assert 'test_table1' in tables
            assert 'test_table2' in tables
            conn.close()
        finally:
            os.unlink(db_path)


class TestGetTableStats:
    """Test table statistics functionality"""
    
    def test_get_table_stats_valid_table(self):
        """Test getting stats for valid table"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            # Create test table with data
            conn.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
            conn.execute("INSERT INTO test_table VALUES (1, 'test1')")
            conn.execute("INSERT INTO test_table VALUES (2, 'test2')")
            conn.commit()
            
            stats = get_table_stats(conn, 'test_table')
            assert stats['count'] == 2
            assert 'id' in stats['columns']
            assert 'name' in stats['columns']
            conn.close()
        finally:
            os.unlink(db_path)

    def test_get_table_stats_nonexistent_table(self):
        """Test getting stats for nonexistent table"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            # Create one table
            conn.execute("CREATE TABLE existing_table (id INTEGER)")
            conn.commit()
            
            with pytest.raises(ValueError, match="Table 'nonexistent_table' does not exist"):
                get_table_stats(conn, 'nonexistent_table')
            conn.close()
        finally:
            os.unlink(db_path)

    def test_get_table_stats_sql_injection_protection(self):
        """Test SQL injection protection in table stats"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            # Create test table
            conn.execute("CREATE TABLE sources (id INTEGER)")
            conn.commit()
            
            # Test malicious table name
            malicious_table = "sources; DROP TABLE test; --"
            with pytest.raises(ValueError, match="does not exist in database"):
                get_table_stats(conn, malicious_table)
            conn.close()
        finally:
            os.unlink(db_path)


class TestInspectDatabase:
    """Test database inspection functionality"""
    
    def test_inspect_database_empty(self):
        """Test inspecting empty database"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            conn.close()
            
            # This would normally print to stdout, but we can't easily test that
            # Just ensure it doesn't crash
            inspect_database(db_path, detailed=False)
        finally:
            os.unlink(db_path)

    def test_inspect_database_with_tables(self):
        """Test inspecting database with tables"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            # Create test tables
            conn.execute("CREATE TABLE sources (id INTEGER, title TEXT)")
            conn.execute("CREATE TABLE documents (id INTEGER, source_id INTEGER)")
            conn.execute("INSERT INTO sources VALUES (1, 'Test Source')")
            conn.execute("INSERT INTO documents VALUES (1, 1)")
            conn.commit()
            conn.close()
            
            # Should not crash
            inspect_database(db_path, detailed=True)
        finally:
            os.unlink(db_path)


class TestShowFunctions:
    """Test display functions (these mainly print to stdout)"""
    
    def test_show_recent_events_empty(self):
        """Test showing recent events from empty database"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            # Should not crash even with no research_events table
            show_recent_events(conn, limit=5)
            conn.close()
        finally:
            os.unlink(db_path)

    def test_show_top_sources_empty(self):
        """Test showing top sources from empty database"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            # Should not crash even with no sources table
            show_top_sources(conn, limit=5)
            conn.close()
        finally:
            os.unlink(db_path)

    def test_show_entity_distribution_empty(self):
        """Test showing entity distribution from empty database"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            # Should not crash even with no entities table
            get_entity_distribution(conn)
            conn.close()
        finally:
            os.unlink(db_path)


class TestDistributionFunctions:
    """Test distribution analysis functions"""
    
    def test_get_event_type_distribution_empty(self):
        """Test event type distribution with empty database"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            # Should not crash even with no research_events table
            get_event_type_distribution(conn)
            conn.close()
        finally:
            os.unlink(db_path)

    def test_get_domain_distribution_empty(self):
        """Test domain distribution with empty database"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = connect_db(db_path)
            # Should not crash even with no research_events table
            get_domain_distribution(conn)
            conn.close()
        finally:
            os.unlink(db_path)