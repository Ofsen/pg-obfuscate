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

def test_process_table_pk_batch(mock_db, sample_config):
    # Setup mock data for iter_rows
    mock_db.iter_rows.return_value = [
        {"id": 1, "email": "a@b.com", "age": 30},
        {"id": 2, "email": "c@d.com", "age": 40},
    ]
    
    # Mock update_batch to return row count
    mock_db.update_batch.return_value = 2
    
    # Mock get_column_types
    mock_db.get_column_types.return_value = {"id": "int4", "email": "varchar", "age": "int4"}

    obfuscator = Obfuscator(mock_db, sample_config)
    result = obfuscator._process_table(sample_config.tables[0])
    
    assert result["success"] is True
    # Rows affected comes from update_batch return value
    assert result["rows_affected"] == 2
    
    # Verify we called iter_rows with schema
    mock_db.iter_rows.assert_called_once()
    assert mock_db.iter_rows.call_args[0][0] == "public"
    
    # Verify we called get_column_types
    mock_db.get_column_types.assert_called()
    
    # Verify update_batch was called with correct data
    mock_db.update_batch.assert_called()
    args = mock_db.update_batch.call_args_list[0]
    
    # update_batch(schema_name, table_name, pk_columns, batch_data, update_columns, column_types)
    # Check update columns (should include email AND age)
    update_cols = args[0][4]
    assert "email" in update_cols
    assert "age" in update_cols
    
    # Check column types passed
    types = args[0][5]
    assert types["email"] == "varchar"
    
    # Check batch payload
    batch_data = args[0][3]
    assert len(batch_data) == 2
    assert batch_data[0]["id"] == 1
    assert batch_data[1]["id"] == 2

def test_process_table_ctid(mock_db, sample_config):
    # Simulate no PK
    mock_db.get_primary_key.return_value = []
    mock_db.iter_rows.return_value = [
        {"ctid": "(0,1)", "email": "a@b.com", "age": 30}
    ]
    mock_db.update_batch.return_value = 1
    
    # Mock get_column_types
    mock_db.get_column_types.return_value = {"email": "varchar", "age": "int4"}
    
    obfuscator = Obfuscator(mock_db, sample_config)
    obfuscator._process_table(sample_config.tables[0])
    
    # Verify update_batch uses ctid
    mock_db.update_batch.assert_called_once()
    args = mock_db.update_batch.call_args
    # update_batch(schema_name, table_name, pk_columns, batch_data, ...)
    batch_data = args[0][3]
    assert batch_data[0]["ctid"] == "(0,1)"

def test_error_rollback(mock_db, sample_config):
    mock_db.iter_rows.side_effect = Exception("DB Error")
    # Mock get_column_types for the try block
    mock_db.get_column_types.return_value = {}
    
    obfuscator = Obfuscator(mock_db, sample_config)
    result = obfuscator._process_table(sample_config.tables[0])
    
    assert result["success"] is False
    assert "DB Error" in result["error"]
    mock_db.rollback.assert_called_once()

