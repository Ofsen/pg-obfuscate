"""CLI entry point for pg-obfuscate."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from pg_obfuscate import __version__
from pg_obfuscate.config import load_config, ConfigError
from pg_obfuscate.db import Database, DatabaseError
from pg_obfuscate.obfuscator import Obfuscator

app = typer.Typer(
    name="pg-obfuscate",
    help="A deterministic PostgreSQL database obfuscation CLI tool.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"pg-obfuscate version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """pg-obfuscate: Deterministic PostgreSQL database obfuscation."""
    pass


@app.command()
def run(
    db_url: str = typer.Option(
        ...,
        "--db-url",
        help="PostgreSQL connection string.",
        envvar="PG_OBFUSCATE_DB_URL",
    ),
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to YAML configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate config and show affected rows/columns without making changes.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt.",
    ),
) -> None:
    """Execute obfuscation on the database."""
    try:
        # Load configuration
        cfg = load_config(config)
        console.print(f"[green]✓[/green] Loaded config from {config}")

        # Connect to database
        db = Database(db_url)
        console.print(f"[green]✓[/green] Connected to database")

        # Get affected tables info
        obfuscator = Obfuscator(db, cfg)
        summary = obfuscator.get_summary()

        # Display summary table
        table = Table(title="Obfuscation Summary")
        table.add_column("Table", style="cyan")
        table.add_column("Columns", style="magenta")
        table.add_column("Rows", justify="right", style="green")

        for table_info in summary:
            table.add_row(
                table_info["table"],
                ", ".join(table_info["columns"]),
                str(table_info["row_count"]),
            )

        console.print(table)

        if dry_run:
            console.print("\n[yellow]Dry run mode[/yellow] - no changes made.")
            raise typer.Exit(0)

        # Confirmation prompt
        if not force:
            console.print("\n[bold red]⚠ WARNING:[/bold red] Make sure you have a backup!")
            confirm = typer.confirm("Proceed with obfuscation?", default=False)
            if not confirm:
                console.print("Aborted.")
                raise typer.Exit(0)

        # Execute obfuscation
        console.print("\n[bold]Executing obfuscation...[/bold]")
        results = obfuscator.execute()

        # Display results
        for result in results:
            if result["success"]:
                console.print(
                    f"[green]✓[/green] {result['table']}: {result['rows_affected']} rows updated"
                )
            else:
                console.print(
                    f"[red]✗[/red] {result['table']}: {result['error']}"
                )

        console.print("\n[bold green]Obfuscation complete![/bold green]")

    except ConfigError as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(2)
    except DatabaseError as e:
        console.print(f"[red]Database error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def validate(
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to YAML configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    db_url: Optional[str] = typer.Option(
        None,
        "--db-url",
        help="PostgreSQL connection string (optional, validates against schema if provided).",
        envvar="PG_OBFUSCATE_DB_URL",
    ),
) -> None:
    """Validate configuration file."""
    try:
        cfg = load_config(config)
        console.print(f"[green]✓[/green] Config syntax is valid")

        if db_url:
            db = Database(db_url)
            errors = cfg.validate_against_schema(db.get_schema())
            if errors:
                for error in errors:
                    console.print(f"[red]✗[/red] {error}")
                raise typer.Exit(2)
            console.print(f"[green]✓[/green] Config matches database schema")

        console.print("\n[bold green]Validation passed![/bold green]")

    except ConfigError as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(2)
    except DatabaseError as e:
        console.print(f"[red]Database error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
