"""Core obfuscation engine."""

from typing import Any

from pg_obfuscate.config import Config, ColumnConfig
from pg_obfuscate.db import Database
from pg_obfuscate.strategies.base import BaseStrategy
from pg_obfuscate.strategies.hash import HashStrategy
from pg_obfuscate.strategies.fake import FakeStrategy
from pg_obfuscate.strategies.null import NullStrategy
from pg_obfuscate.strategies.preserve import PreserveStrategy


class Obfuscator:
    """Core obfuscation engine."""

    def __init__(self, db: Database, config: Config):
        """Initialize obfuscator.
        
        Args:
            db: Database connection
            config: Parsed configuration
        """
        self.db = db
        self.config = config
        self._strategies: dict[str, BaseStrategy] = {}

    def _get_strategy(self, column_config: ColumnConfig) -> BaseStrategy:
        """Get or create strategy for a column config.
        
        Args:
            column_config: Column configuration
            
        Returns:
            Strategy instance
        """
        # Create cache key
        key = f"{column_config.strategy}:{column_config.strategy_type or ''}"
        
        if key not in self._strategies:
            if column_config.strategy == "hash":
                self._strategies[key] = HashStrategy()
            elif column_config.strategy == "fake":
                self._strategies[key] = FakeStrategy(column_config.strategy_type)
            elif column_config.strategy == "null":
                self._strategies[key] = NullStrategy()
            elif column_config.strategy == "preserve":
                self._strategies[key] = PreserveStrategy()
            else:
                raise ValueError(f"Unknown strategy: {column_config.strategy}")
        
        return self._strategies[key]

    def get_summary(self) -> list[dict[str, Any]]:
        """Get summary of tables/columns/rows to be affected.
        
        Returns:
            List of dicts with table, columns, and row_count
        """
        summary = []
        for table_config in self.config.tables:
            row_count = self.db.get_row_count(table_config.name)
            summary.append({
                "table": table_config.name,
                "columns": [col.name for col in table_config.columns],
                "row_count": row_count,
            })
        return summary

    def execute(self) -> list[dict[str, Any]]:
        """Execute obfuscation on all configured tables.
        
        Returns:
            List of result dicts per table
        """
        results = []
        
        for table_config in self.config.tables:
            result = self._process_table(table_config)
            results.append(result)
        
        return results

    def _process_table(self, table_config) -> dict[str, Any]:
        """Process a single table.
        
        Args:
            table_config: Table configuration
            
        Returns:
            Result dict with success status and row count
        """
        table_name = table_config.name
        column_names = [col.name for col in table_config.columns]
        
        try:
            # Get primary key columns
            pk_columns = self.db.get_primary_key(table_name)
            use_ctid = len(pk_columns) == 0
            
            # Fetch rows
            if use_ctid:
                rows = self.db.fetch_rows_with_ctid(table_name, column_names)
            else:
                rows = self.db.fetch_rows(table_name, column_names, pk_columns)
            
            rows_affected = 0
            
            for row in rows:
                updates = {}
                
                for col_config in table_config.columns:
                    col_name = col_config.name
                    original_value = row.get(col_name)
                    
                    # Compute deterministic seed
                    seed = BaseStrategy.compute_seed(
                        self.config.seed,
                        table_name,
                        col_name,
                        original_value,
                    )
                    
                    # Get strategy and obfuscate
                    strategy = self._get_strategy(col_config)
                    new_value = strategy.obfuscate(original_value, seed)
                    
                    # Only update if value changed
                    if new_value != original_value:
                        updates[col_name] = new_value
                
                # Apply updates
                if updates:
                    if use_ctid:
                        self.db.update_row_by_ctid(table_name, row["ctid"], updates)
                    else:
                        pk_values = {pk: row[pk] for pk in pk_columns}
                        self.db.update_row(table_name, pk_columns, pk_values, updates)
                    rows_affected += 1
            
            # Commit transaction for this table
            self.db.commit()
            
            return {
                "table": table_name,
                "success": True,
                "rows_affected": rows_affected,
            }
            
        except Exception as e:
            # Rollback on error
            self.db.rollback()
            return {
                "table": table_name,
                "success": False,
                "error": str(e),
                "rows_affected": 0,
            }
