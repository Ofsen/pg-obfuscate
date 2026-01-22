# pg-obfuscate

pg-obfuscate is an open-source, developer-first CLI tool that deterministically obfuscates
sensitive data in PostgreSQL databases.

It allows teams to safely share production-like datasets across development,
staging, and testing environments without leaking real user data.

pg-obfuscate is designed to be:

- **Deterministic** - Same input + same config = same output
- **Schema-aware** - Target `public` or custom schemas (e.g., `auth.users`)
- **Scalable** - Uses server-side cursors and batch updates for high performance and low memory footprint
- **Safe by default** - Dry-run mode, confirmation prompts, and integer overflow protection
- **Extensible** - Multiple obfuscation strategies with precise type casting

> [!CAUTION]
> **This tool is inherently DESTRUCTIVE.**
> `pg-obfuscate` modifies data in-place. It is designed to be run on **clones** or **backups** of production data, never on the live production database itself. There is no "undo" button.

## Installation

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

## Quick Start

1. Create a config file:

```yaml
seed: 12345
tables:
  # Tables default to 'public' schema
  users:
    email: fake:email
    name: fake:name
  # Access other schemas using schema.table
  auth.accounts:
    username:
      strategy: fake:username
      consistency_group: user_handles
    password_hash: hash
```

2. Run with dry-run first:

```bash
pg-obfuscate run --db-url postgres://user:pass@localhost/db --config config.yaml --dry-run
```

3. Execute obfuscation:

```bash
pg-obfuscate run --db-url postgres://user:pass@localhost/db --config config.yaml
```

## Performance & Scalability

`pg-obfuscate` is designed to handle production-scale databases:

- **Streaming**: Data is streamed from PostgreSQL using server-side cursors, preventing Out-of-Memory (OOM) errors even on million-row tables.
- **Batching**: Updates are executed in batches (2,000 rows by default) to minimize network round-trips and maximize throughput.
- **Type Safety**: Automatically detects column types to apply explicit casting (e.g., `v::timestamp`), ensuring compatibility with complex PostgreSQL types.
- **PK-less Support**: Works on tables without primary keys by automatically falling back to PostgreSQL's internal `ctid` for row identification.
- **Integer Safety**: Automatically detects `smallint` (int2) and `integer` (int4) columns to prevent overflow errors during data generation.

## Commands

| Command                  | Description                                  |
| ------------------------ | -------------------------------------------- |
| `pg-obfuscate run`       | Execute obfuscation                          |
| `pg-obfuscate validate`  | Validate config (optional: check against DB) |
| `pg-obfuscate --version` | Show version                                 |

## Obfuscation Strategies

| Strategy      | Description                     |
| ------------- | ------------------------------- |
| `hash`        | SHA256 hash (text columns only) |
| `fake:<type>` | Faker-generated data            |
| `null`        | Set to NULL                     |
| `preserve`    | Keep original value             |

### Consistency Groups

Consistency groups ensure that different columns (even in different tables) produce the same obfuscated output for the same input value. This is essential for maintaining referential integrity across your database.

```yaml
tables:
  users:
    email:
      strategy: fake:email
      consistency_group: user_emails
  newsletter_subs:
    subscriber_email:
      strategy: fake:email
      consistency_group: user_emails
```

### NULL Preservation

By default, `pg-obfuscate` preserves `NULL` values. If a source column contains a `NULL`, the tool will skip it regardless of the strategy (except for the explicit `null` strategy). This ensures you don't accidentally introduce data into rows that were intentionally empty.

### Schema Validation

Before running a destructive obfuscation, you can validate your configuration against the actual database schema to catch typos or missing columns:

```bash
pg-obfuscate validate --config config.yaml --db-url postgres://user:pass@localhost/db
```

This will verify that every table and column listed in your config exists in the database and is accessible.

### Supported Fake Types

**Text types:** `email`, `name`, `first_name`, `last_name`, `phone`, `address`, `company`, `text`, `city`, `country`, `postcode`, `street_address`, `job`, `url`, `username`, `uuid`

**Numeric types:** `int`, `number`, `float`, `decimal`, `price`

**Date types:** `date`, `datetime`

## Safety Features

- `--dry-run` - Preview without making changes
- `--force` - Skip confirmation prompt
- Confirmation prompt before execution
- Backup warning displayed
- Per-table transactions (rollback on error)
- Integer range enforcement (prevents overflow crashes)

## Safety & Backup Guidelines

### 1. Never Run on Live Production

This tool is intended for creating sanitized datasets for development. Always run it on a restored backup or a database fork.

### 2. Transactional Behavior (Atomicity)

`pg-obfuscate` processes tables one by one.

- If an error occurs during the processing of a table, that **specific table** will be rolled back.
- However, any tables processed **before** the error occurred will remain obfuscated (committed).
- If the process is killed (e.g., `Ctrl+C`), the current batch may be partially committed or rolled back depending on the exact timing.

### 3. Recommended Workflow

1.  **Backup:** Create a full dump of your database (`pg_dump`).
2.  **Restore:** Restore the dump to a dedicated staging/local database.
3.  **Validate:** Run `pg-obfuscate validate --config config.yaml` to check for schema mismatches.
4.  **Dry-run:** Run `pg-obfuscate run --dry-run` to see which tables will be affected.
5.  **Execute:** Run the obfuscation on the restored clone.
6.  **Verify:** Check the data to ensure relational integrity and obfuscation quality before sharing with the team.

## Exit Codes

| Code | Meaning                 |
| ---- | ----------------------- |
| 0    | Success                 |
| 1    | Runtime error           |
| 2    | Config validation error |

## Environment Variables

- `PG_OBFUSCATE_DB_URL` - Database connection string

## License & Commercial Use

This project is licensed under a **Dual-Licensing** model to support both the open-source community and commercial enterprise needs.

### 1. Open Source License (AGPLv3)

For individuals, small teams, and open-source projects, `pg-obfuscate` is available under the **GNU Affero General Public License v3.0 (AGPLv3)**. See the [LICENSE](LICENSE) file for the full text.

This means:

- You are free to use, modify, and distribute the software
- If you use it in a service or internal tool, you must make your modifications available under the same license

### 2. Commercial License

For companies that cannot or do not wish to comply with the AGPLv3, we offer a [**Commercial License**](COMMERCIAL_LICENSE.md) that provides:

- Use in proprietary/internal systems
- No obligation to release source code

**For licensing inquiries, custom strategies, or commercial quotes, please contact:**
ofsen@proton.me
