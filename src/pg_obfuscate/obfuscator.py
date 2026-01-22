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

    STRATEGY_CLASSES = {
        "hash": HashStrategy,
        "null": NullStrategy,
        "preserve": PreserveStrategy,
    }

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
            strat_name = column_config.strategy
            
            if strat_name == "fake":
                self._strategies[key] = FakeStrategy(column_config.strategy_type)
            elif strat_name in self.STRATEGY_CLASSES:
                self._strategies[key] = self.STRATEGY_CLASSES[strat_name]()
            else:
                raise ValueError(f"Unknown strategy: {strat_name}")
        
        return self._strategies[key]

    def get_summary(self) -> list[dict[str, Any]]:
        """Get summary of tables/columns/rows to be affected.
        
        Returns:
            List of dicts with table, columns, and row_count
        """
        summary = []
        for table_config in self.config.tables:
            row_count = self.db.get_row_count(table_config.schema, table_config.name)
            summary.append({
                "table": table_config.qualified_name,
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
        """Process a single table using batch processing.
        
        Args:
            table_config: Table configuration
            
        Returns:
            Result dict with success status and row count
        """
        schema_name = table_config.schema
        table_name = table_config.name
        # Ensure we fetch all configured columns
        column_names = [col.name for col in table_config.columns]
        
        try:
            # Get primary key columns
            pk_columns = self.db.get_primary_key(schema_name, table_name)
            
            # Fetch column types for casting and strategy limits
            column_types = self.db.get_column_types(schema_name, table_name)
            
            rows_affected = 0
            batch_updates = []
            BATCH_SIZE = 2000
            
            # Iterate over rows (streaming)
            for row in self.db.iter_rows(schema_name, table_name, column_names, pk_columns, batch_size=BATCH_SIZE):
                updates = {}
                
                # Determine Identity (PK or ctid)
                identity = {}
                if pk_columns:
                    for pk in pk_columns:
                        identity[pk] = row[pk]
                else:
                    identity["ctid"] = row["ctid"]

                # Process columns
                for col_config in table_config.columns:
                    col_name = col_config.name
                    original_value = row.get(col_name)
                    
                    # Compute deterministic seed
                    seed = BaseStrategy.compute_seed(
                        self.config.seed,
                        table_config.qualified_name,
                        col_name,
                        original_value,
                        group=col_config.consistency_group,
                    )
                    
                    # Get strategy
                    strategy = self._get_strategy(col_config)
                    
                    # Pass column type info if available (for integer safety)
                    col_type = column_types.get(col_name)
                    new_value = strategy.obfuscate(original_value, seed, col_type)
                    
                    # For batch updates, we must provide values for all columns
                    updates[col_name] = new_value
                
                # Add to batch
                if updates:
                    # Merge identity and updates for the batch payload
                    batch_item = {**identity, **updates}
                    batch_updates.append(batch_item)
                
                # Flush batch if full
                if len(batch_updates) >= BATCH_SIZE:
                    rows_affected += self.db.update_batch(
                        schema_name,
                        table_name,
                        pk_columns,
                        batch_updates,
                        column_names,
                        column_types
                    )
                    batch_updates = []
            
            # Flush remaining items
            if batch_updates:
                rows_affected += self.db.update_batch(
                    schema_name,
                    table_name,
                    pk_columns,
                    batch_updates,
                    column_names,
                    column_types
                )
            
            # Commit transaction for this table (Warning: Per-table atomicity only)
            self.db.commit()
            
            return {
                "table": table_config.qualified_name,
                "success": True,
                "rows_affected": rows_affected,
            }
            
        except Exception as e:
            # Rollback on error
            self.db.rollback()
            return {
                "table": table_config.qualified_name,
                "success": False,
                "error": str(e),
                "rows_affected": 0,
            }
