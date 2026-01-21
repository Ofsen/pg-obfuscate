
import psycopg2
from rich.console import Console
from rich.table import Table

def verify():
    conn = psycopg2.connect("postgres://postgres:postgres@localhost:5432/postgres")
    console = Console()
    
    tables = ["users", "orders", "profiles"]
    
    for table_name in tables:
        console.print(f"\n[bold cyan]Table: {table_name}[/bold cyan]")
        
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {table_name} LIMIT 5")
            rows = cur.fetchall()
            if not rows:
                console.print("No rows found.")
                continue
                
            # Get column names
            col_names = [desc[0] for desc in cur.description]
            
            table = Table()
            for col in col_names:
                table.add_column(col)
                
            for row in rows:
                table.add_row(*[str(val) for val in row])
                
            console.print(table)

    conn.close()

if __name__ == "__main__":
    verify()
