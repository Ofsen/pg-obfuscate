"""Configuration parsing and validation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Configuration error."""
    pass


@dataclass
class ColumnConfig:
    """Configuration for a single column."""
    name: str
    strategy: str
    strategy_type: str | None = None  # For fake:email, fake:name, etc.

    @classmethod
    def from_value(cls, name: str, value: str | None) -> "ColumnConfig":
        """Parse column config from YAML value."""
        # Handle YAML null -> null strategy
        if value is None:
            return cls(name=name, strategy="null", strategy_type=None)
        
        if ":" in value:
            strategy, strategy_type = value.split(":", 1)
        else:
            strategy = value
            strategy_type = None
        
        valid_strategies = {"hash", "fake", "null", "preserve"}
        if strategy not in valid_strategies:
            raise ConfigError(f"Invalid strategy '{strategy}' for column '{name}'")
        
        if strategy == "fake" and not strategy_type:
            raise ConfigError(f"fake strategy requires a type (e.g., fake:email) for column '{name}'")
        
        return cls(name=name, strategy=strategy, strategy_type=strategy_type)


@dataclass
class TableConfig:
    """Configuration for a single table."""
    name: str
    schema: str = "public"
    columns: list[ColumnConfig] = field(default_factory=list)

    @property
    def qualified_name(self) -> str:
        """Get schema-qualified name (schema.table)."""
        return f"{self.schema}.{self.name}"

    @classmethod
    def from_dict(cls, key: str, columns: dict[str, str]) -> "TableConfig":
        """Parse table config from YAML dict key and columns.
        
        Args:
            key: Table name key (e.g. 'users' or 'auth.users')
            columns: Column config dict
        """
        if "." in key:
            schema_name, table_name = key.split(".", 1)
        else:
            schema_name = "public"
            table_name = key
            
        column_configs = [
            ColumnConfig.from_value(col_name, strategy)
            for col_name, strategy in columns.items()
        ]
        return cls(name=table_name, schema=schema_name, columns=column_configs)


@dataclass
class Config:
    """Main configuration."""
    seed: int
    tables: list[TableConfig] = field(default_factory=list)

    def validate_against_schema(self, schema: dict[str, list[str]]) -> list[str]:
        """Validate config against database schema.
        
        Args:
            schema: Dict mapping table names to list of column names
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        for table in self.tables:
            # We assume schema keys are qualified 'schema.table'
            # But the DB.get_schema needs to change first to return qualified keys.
            # We will handle backward compatibility or update DB concurrently.
            # Let's assume schema keys will be 'schema.table'
            
            # Try qualified match first
            if table.qualified_name not in schema:
                errors.append(f"Table '{table.qualified_name}' not found in database")
                continue
            
            db_columns = schema[table.qualified_name]
            for column in table.columns:
                if column.name not in db_columns:
                    errors.append(
                        f"Column '{column.name}' not found in table '{table.qualified_name}'"
                    )
        
        return errors


def load_config(path: Path) -> Config:
    """Load and parse configuration from YAML file.
    
    Args:
        path: Path to YAML config file
        
    Returns:
        Parsed Config object
        
    Raises:
        ConfigError: If config is invalid
    """
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")
    except IOError as e:
        raise ConfigError(f"Could not read config file: {e}")
    
    if not isinstance(data, dict):
        raise ConfigError("Config must be a YAML object")
    
    # Parse seed
    seed = data.get("seed")
    if seed is None:
        raise ConfigError("Config must have a 'seed' field")
    if not isinstance(seed, int):
        raise ConfigError("'seed' must be an integer")
    
    # Parse tables
    tables_data = data.get("tables", {})
    if not isinstance(tables_data, dict):
        raise ConfigError("'tables' must be a YAML object")
    
    tables = [
        TableConfig.from_dict(table_name, columns)
        for table_name, columns in tables_data.items()
    ]
    
    if not tables:
        raise ConfigError("Config must have at least one table")
    
    return Config(seed=seed, tables=tables)
