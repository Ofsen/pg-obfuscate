"""Database connection and schema operations."""

from typing import Any

import psycopg2
from psycopg2 import sql


class DatabaseError(Exception):
    """Database operation error."""
    pass


class Database:
    """PostgreSQL database connection and operations."""

    def __init__(self, connection_string: str):
        """Initialize database connection.
        
        Args:
            connection_string: PostgreSQL connection URL
            
        Raises:
            DatabaseError: If connection fails
        """
        try:
            self.conn = psycopg2.connect(connection_string)
            self.conn.autocommit = False
        except psycopg2.Error as e:
            raise DatabaseError(f"Failed to connect: {e}")

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def get_schema(self) -> dict[str, list[str]]:
        """Get database schema.
        
        Returns:
            Dict mapping table names to list of column names
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """)
            
            schema: dict[str, list[str]] = {}
            for table_name, column_name in cur.fetchall():
                if table_name not in schema:
                    schema[table_name] = []
                schema[table_name].append(column_name)
            
            return schema

    def get_primary_key(self, table_name: str) -> list[str]:
        """Get primary key columns for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of primary key column names (empty if none)
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass
                AND i.indisprimary
                ORDER BY array_position(i.indkey, a.attnum)
            """, (table_name,))
            
            return [row[0] for row in cur.fetchall()]

    def get_row_count(self, table_name: str) -> int:
        """Get row count for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Number of rows
        """
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(
                    sql.Identifier(table_name)
                )
            )
            result = cur.fetchone()
            return result[0] if result else 0

    def fetch_rows(self, table_name: str, columns: list[str], pk_columns: list[str]) -> list[dict[str, Any]]:
        """Fetch rows from table with specified columns.
        
        Args:
            table_name: Name of the table
            columns: Columns to fetch for obfuscation
            pk_columns: Primary key columns for identification
            
        Returns:
            List of dicts with column values
        """
        all_columns = list(set(pk_columns + columns))
        
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT {} FROM {}").format(
                    sql.SQL(", ").join(sql.Identifier(c) for c in all_columns),
                    sql.Identifier(table_name)
                )
            )
            
            rows = []
            for row in cur.fetchall():
                rows.append(dict(zip(all_columns, row)))
            
            return rows

    def update_row(
        self,
        table_name: str,
        pk_columns: list[str],
        pk_values: dict[str, Any],
        updates: dict[str, Any],
    ) -> None:
        """Update a single row.
        
        Args:
            table_name: Name of the table
            pk_columns: Primary key column names
            pk_values: Primary key values for WHERE clause
            updates: Column -> new value mapping
        """
        if not updates:
            return
            
        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(col))
            for col in updates.keys()
        )
        
        where_clause = sql.SQL(" AND ").join(
            sql.SQL("{} = %s").format(sql.Identifier(col))
            for col in pk_columns
        )
        
        query = sql.SQL("UPDATE {} SET {} WHERE {}").format(
            sql.Identifier(table_name),
            set_clause,
            where_clause,
        )
        
        values = list(updates.values()) + [pk_values[col] for col in pk_columns]
        
        with self.conn.cursor() as cur:
            cur.execute(query, values)

    def update_row_by_ctid(
        self,
        table_name: str,
        ctid: Any,
        updates: dict[str, Any],
    ) -> None:
        """Update a single row using ctid (when no primary key).
        
        Args:
            table_name: Name of the table
            ctid: Row's ctid value
            updates: Column -> new value mapping
        """
        if not updates:
            return
            
        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(col))
            for col in updates.keys()
        )
        
        query = sql.SQL("UPDATE {} SET {} WHERE ctid = %s").format(
            sql.Identifier(table_name),
            set_clause,
        )
        
        values = list(updates.values()) + [ctid]
        
        with self.conn.cursor() as cur:
            cur.execute(query, values)

    def fetch_rows_with_ctid(self, table_name: str, columns: list[str]) -> list[dict[str, Any]]:
        """Fetch rows from table with ctid for tables without primary key.
        
        Args:
            table_name: Name of the table
            columns: Columns to fetch for obfuscation
            
        Returns:
            List of dicts with column values including ctid
        """
        all_columns = ["ctid"] + columns
        
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT ctid, {} FROM {}").format(
                    sql.SQL(", ").join(sql.Identifier(c) for c in columns),
                    sql.Identifier(table_name)
                )
            )
            
            rows = []
            for row in cur.fetchall():
                rows.append(dict(zip(all_columns, row)))
            
            return rows

    def commit(self) -> None:
        """Commit current transaction."""
        self.conn.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.conn.rollback()
