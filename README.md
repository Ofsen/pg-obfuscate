# pg-obfuscate

A deterministic PostgreSQL database obfuscation CLI tool.

## Features

- **Deterministic** - Same input + same config = same output
- **Safe by default** - Dry-run mode, confirmation prompts, backup warnings
- **Extensible** - Multiple obfuscation strategies
- **CI-friendly** - Clear exit codes, structured output

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
  users:
    email: fake:email
    name: fake:name
    phone: null
  payments:
    card_number: hash
    amount: preserve
```

2. Run with dry-run first:

```bash
pg-obfuscate run --db-url postgres://user:pass@localhost/db --config config.yaml --dry-run
```

3. Execute obfuscation:

```bash
pg-obfuscate run --db-url postgres://user:pass@localhost/db --config config.yaml
```

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

**Numeric types:** `int`, `number`, `float`, `decimal`

**Date types:** `date`, `datetime`

## Configuration

```yaml
# Global seed for determinism
seed: 12345

# Tables to obfuscate
tables:
  users:
    email: fake:email # Generate fake email
    name: fake:name # Generate fake name
    ssn: hash # Hash the value
    notes: null # Set to NULL
    id: preserve # Keep unchanged
```

## Safety Features

- `--dry-run` - Preview without making changes
- Confirmation prompt before execution
- Backup warning displayed
- Per-table transactions (rollback on error)

## Exit Codes

| Code | Meaning                 |
| ---- | ----------------------- |
| 0    | Success                 |
| 1    | Runtime error           |
| 2    | Config validation error |

## Environment Variables

- `PG_OBFUSCATE_DB_URL` - Database connection string
