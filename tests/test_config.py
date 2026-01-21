"""Unit tests for config parsing and validation."""

import pytest
import yaml
from pg_obfuscate.config import load_config, ConfigError

def test_load_valid_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
seed: 12345
tables:
  users:
    email: fake:email
    name: fake:name
    age: null
    id: preserve
    hash_col: hash
""")
    
    config = load_config(config_file)
    assert config.seed == 12345
    assert len(config.tables) == 1
    
    table = config.tables[0]
    assert table.name == "users"
    assert len(table.columns) == 5
    
    # Check column configs
    email = next(c for c in table.columns if c.name == "email")
    assert email.strategy == "fake"
    assert email.strategy_type == "email"
    
    age = next(c for c in table.columns if c.name == "age")
    assert age.strategy == "null"
    
    hash_col = next(c for c in table.columns if c.name == "hash_col")
    assert hash_col.strategy == "hash"

def test_load_invalid_strategy(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
seed: 123
tables:
  t:
    c: invalid_strategy
""")
    with pytest.raises(ConfigError, match="Invalid strategy"):
        load_config(config_file)

def test_load_missing_seed(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
tables:
  t:
    c: null
""")
    with pytest.raises(ConfigError, match="must have a 'seed'"):
        load_config(config_file)

def test_fake_missing_type(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
seed: 123
tables:
  t:
    c: fake
""")
    with pytest.raises(ConfigError, match="fake strategy requires a type"):
        load_config(config_file)

def test_validate_against_schema(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
seed: 123
tables:
  users:
    email: null
    unknown_col: null
  unknown_table:
    id: null
""")
    config = load_config(config_file)
    
    schema = {
        "public.users": ["id", "email", "name"],
        "public.orders": ["id", "total"]
    }
    
    errors = config.validate_against_schema(schema)
    assert len(errors) == 2
    error_messages = set(errors)
    assert "Table 'public.unknown_table' not found in database" in error_messages
    assert "Column 'unknown_col' not found in table 'public.users'" in error_messages
