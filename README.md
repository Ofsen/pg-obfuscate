# pg-obfuscate

pg-obfuscate is a developer-first CLI tool that deterministically obfuscates
sensitive data in PostgreSQL databases.

It allows teams to safely share production-like datasets across development,
staging, and testing environments without leaking real user data.

pg-obfuscate is designed to be:

- **Deterministic** - Same input + same config = same output
- **Schema-aware** - Target `public` or custom schemas (e.g., `auth.users`)
- **Scalable** - Uses server-side cursors and batch updates for high performance and low memory footprint
- **Safe by default** - Dry-run mode, confirmation prompts, and integer overflow protection
- **Extensible** - Multiple obfuscation strategies with precise type casting

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
    username: fake:username
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
- **Integer Safety**: Automatically detects `smallint` (int2) and `integer` (int4) columns to prevent overflow errors during data generation.

## Commands

| Command                  | Description          |
| ------------------------ | -------------------- |
| `pg-obfuscate run`       | Execute obfuscation  |
| `pg-obfuscate validate`  | Validate config file |
| `pg-obfuscate --version` | Show version         |

## Obfuscation Strategies

| Strategy      | Description                     |
| ------------- | ------------------------------- |
| `hash`        | SHA256 hash (text columns only) |
| `fake:<type>` | Faker-generated data            |
| `null`        | Set to NULL                     |
| `preserve`    | Keep original value             |

### Supported Fake Types

**Text types:** `email`, `name`, `first_name`, `last_name`, `phone`, `address`, `company`, `text`, `city`, `country`, `postcode`, `street_address`, `job`, `url`, `username`, `uuid`

**Numeric types:** `int`, `number`, `float`, `decimal` (Magnitude matching + size safety)

**Date types:** `date`, `datetime`

## Safety Features

- `--dry-run` - Preview without making changes
- `--force` - Skip confirmation prompt
- Confirmation prompt before execution
- Backup warning displayed
- Per-table transactions (rollback on error)
- Integer range enforcement (prevents overflow crashes)

## Exit Codes

| Code | Meaning                 |
| ---- | ----------------------- |
| 0    | Success                 |
| 1    | Runtime error           |
| 2    | Config validation error |

## Environment Variables

- `PG_OBFUSCATE_DB_URL` - Database connection string
