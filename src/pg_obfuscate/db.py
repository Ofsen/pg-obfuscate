"""Database connection and schema operations."""

from typing import Any, Iterator, Optional

import psycopg2
from psycopg2 import sql, extras


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
            Dict mapping qualified table names (schema.table) to list of column names
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT table_schema, table_name, column_name
                FROM information_schema.columns
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_schema, table_name, ordinal_position
            """)
            
            schema: dict[str, list[str]] = {}
            for table_schema, table_name, column_name in cur.fetchall():
                qualified_name = f"{table_schema}.{table_name}"
                if qualified_name not in schema:
                    schema[qualified_name] = []
                schema[qualified_name].append(column_name)
            
            return schema

    def get_primary_key(self, schema_name: str, table_name: str) -> list[str]:
        """Get primary key columns for a table.
        
        Args:
            schema_name: Schema name
            table_name: Table name
            
        Returns:
            List of primary key column names (empty if none)
        """
        # PostgreSQL regclass handles schema.table correctly if passed as string
        qualified_name = f"{schema_name}.{table_name}"
        
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass
                AND i.indisprimary
                ORDER BY array_position(i.indkey, a.attnum)
            """, (qualified_name,))
            
            return [row[0] for row in cur.fetchall()]

    def get_row_count(self, schema_name: str, table_name: str) -> int:
        """Get row count for a table.
        
        Args:
            schema_name: Schema name
            table_name: Table name
            
        Returns:
            Number of rows
        """
        with self.conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                    sql.Identifier(schema_name),
                    sql.Identifier(table_name)
                )
            )
            result = cur.fetchone()
            return result[0] if result else 0

    def get_column_types(self, schema_name: str, table_name: str) -> dict[str, str]:
        """Get column types for a table.
        
        Args:
            schema_name: Schema name
            table_name: Table name
            
        Returns:
            Dict mapping column names to their UDT type name (e.g. 'int4', 'varchar')
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, udt_name
                FROM information_schema.columns
                WHERE table_name = %s
                AND table_schema = %s
            """, (table_name, schema_name))
            
            return {row[0]: row[1] for row in cur.fetchall()}

    def iter_rows(
        self,
        schema_name: str,
        table_name: str,
        columns: list[str],
        pk_columns: list[str],
        batch_size: int = 2000
    ) -> Iterator[dict[str, Any]]:
        """Iterate over rows using a server-side cursor.
        
        Args:
            schema_name: Schema name
            table_name: Name of the table
            columns: Columns to fetch for obfuscation
            pk_columns: Primary key columns (empty if using ctid)
            batch_size: Number of rows to fetch from server at once
            
        Yields:
            Dict with column values
        """
        # Determine identifying columns
        if not pk_columns:
            # Use ctid if no PK
            select_cols = ["ctid"] + columns
            cursor_name = f"cur_{schema_name}_{table_name}_ctid"
        else:
            select_cols = list(set(pk_columns + columns))
            cursor_name = f"cur_{schema_name}_{table_name}_pk"

        query = sql.SQL("SELECT {} FROM {}.{}").format(
            sql.SQL(", ").join(sql.Identifier(c) for c in select_cols),
            sql.Identifier(schema_name),
            sql.Identifier(table_name)
        )

        # Use named cursor for server-side streaming
        try:
            with self.conn.cursor(name=cursor_name) as cur:
                cur.itersize = batch_size
                cur.execute(query)
                
                while True:
                    rows = cur.fetchmany(batch_size)
                    if not rows:
                        break
                        
                    for row in rows:
                        yield dict(zip(select_cols, row))
        except psycopg2.Error as e:
            raise DatabaseError(f"Error iterating rows: {e}")

    def update_batch(
        self,
        schema_name: str,
        table_name: str,
        pk_columns: list[str],
        batch_data: list[dict[str, Any]],
        update_columns: list[str],
        column_types: Optional[dict[str, str]] = None
    ) -> int:
        """Update multiple rows in a single query.
        
        Args:
            schema_name: Schema name
            table_name: Name of the table
            pk_columns: Primary key columns (empty if using ctid)
            batch_data: List of dicts containing PK/ctid and new values
            update_columns: List of columns being updated
            column_types: Optional mapping of column names to types for casting
            
        Returns:
            Number of rows updated
        """
        if not batch_data:
            return 0

        # Determine if we use PK or ctid
        use_ctid = not pk_columns
        id_cols = ["ctid"] if use_ctid else pk_columns
        
        # Prepare value tuples for execute_values
        # Structure: (id_val1, id_val2..., update_val1, update_val2...)
        values_list = []
        for item in batch_data:
            row_vals = []
            # Add identity values
            for id_col in id_cols:
                row_vals.append(item[id_col])
            # Add update values
            for col in update_columns:
                row_vals.append(item[col])
            values_list.append(tuple(row_vals))

        # Define columns for the VALUES clause
        # v_pk1, v_pk2..., v_col1, v_col2...
        values_alias_cols = [f"v_id_{i}" for i in range(len(id_cols))]
        values_alias_cols += [f"v_{col}" for col in update_columns]

        # Build SET clause: col1 = v.v_col1::type
        set_assignments = []
        for col in update_columns:
            target_col = sql.Identifier(col)
            source_val = sql.Identifier(f"v_{col}")
            
            # Apply cast if type is known
            if column_types and col in column_types:
                type_name = column_types[col]
                cast_expr = sql.SQL("{}::{}").format(source_val, sql.SQL(type_name))
                assignment = sql.SQL("{} = {}").format(target_col, cast_expr)
            else:
                assignment = sql.SQL("{} = {}").format(target_col, source_val)
            
            set_assignments.append(assignment)

        set_clause = sql.SQL(", ").join(set_assignments)
        
        # Build WHERE clause: t.pk1 = v.v_id_0
        id_assignments = []
        for col, val_alias in zip(id_cols, values_alias_cols[:len(id_cols)]):
            target_col = sql.Identifier(col)
            source_val = sql.Identifier(val_alias)
            
            if column_types and col in column_types:
                type_name = column_types[col]
                cast_expr = sql.SQL("{}::{}").format(source_val, sql.SQL(type_name))
                assignment = sql.SQL("{} = {}").format(target_col, cast_expr)
            elif col == 'ctid':
                assignment = sql.SQL("{} = {}::tid").format(target_col, source_val)
            else:
                assignment = sql.SQL("{} = {}").format(target_col, source_val)
            
            id_assignments.append(assignment)

        where_clause = sql.SQL(" AND ").join(id_assignments)

        # Full query:
        # UPDATE schema.table AS t
        # SET ...
        # FROM (VALUES %s) AS v(...)
        # WHERE ...
        query = sql.SQL(
            "UPDATE {}.{} AS t SET {} FROM (VALUES %s) AS v({}) WHERE {}"
        ).format(
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
            set_clause,
            sql.SQL(", ").join(sql.Identifier(a) for a in values_alias_cols),
            where_clause
        )

        with self.conn.cursor() as cur:
            extras.execute_values(
                cur,
                query,
                values_list,
                template=None,
                page_size=len(batch_data)
            )
            return cur.rowcount

    def commit(self) -> None:
        """Commit current transaction."""
        self.conn.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.conn.rollback()
