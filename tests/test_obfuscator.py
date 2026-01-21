"""Unit tests for obfuscator engine."""

import pytest
from unittest.mock import Mock, call
from pg_obfuscate.obfuscator import Obfuscator
from pg_obfuscate.config import Config, TableConfig, ColumnConfig

@pytest.fixture
def mock_db():
    db = Mock()
    db.get_primary_key.return_value = ["id"]
    return db

@pytest.fixture
def sample_config():
    return Config(
        seed=123,
        tables=[
            TableConfig(
                name="users",
                columns=[
                    ColumnConfig(name="email", strategy="fake", strategy_type="email"),
                    ColumnConfig(name="age", strategy="preserve"),
                ]
            )
        ]
    )

def test_process_table_pk(mock_db, sample_config):
    # Setup mock data
    mock_db.fetch_rows.return_value = [
        {"id": 1, "email": "a@b.com", "age": 30},
        {"id": 2, "email": "c@d.com", "age": 40},
    ]
    
    obfuscator = Obfuscator(mock_db, sample_config)
    result = obfuscator._process_table(sample_config.tables[0])
    
    assert result["success"] is True
    assert result["rows_affected"] > 0
    
    # Check updates
    assert mock_db.update_row.call_count == 2
    
    # Verify preserve strategy didn't change age
    args = mock_db.update_row.call_args_list[0]
    updates = args[0][3]
    assert "age" not in updates
    assert "email" in updates

def test_process_table_ctid(mock_db, sample_config):
    # Simulate no PK
    mock_db.get_primary_key.return_value = []
    mock_db.fetch_rows_with_ctid.return_value = [
        {"ctid": "(0,1)", "email": "a@b.com", "age": 30}
    ]
    
    obfuscator = Obfuscator(mock_db, sample_config)
    obfuscator._process_table(sample_config.tables[0])
    
    mock_db.update_row_by_ctid.assert_called_once()
    args = mock_db.update_row_by_ctid.call_args
    assert args[0][1] == "(0,1)"

def test_error_rollback(mock_db, sample_config):
    mock_db.fetch_rows.side_effect = Exception("DB Error")
    
    obfuscator = Obfuscator(mock_db, sample_config)
    result = obfuscator._process_table(sample_config.tables[0])
    
    assert result["success"] is False
    assert "DB Error" in result["error"]
    mock_db.rollback.assert_called_once()
