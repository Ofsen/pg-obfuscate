import subprocess
import psycopg2
import yaml
import os
from pathlib import Path

# Database URL for testing
DB_URL = os.environ.get("PG_OBFUSCATE_DB_URL", "postgres://postgres:postgres@localhost:5432/postgres")

def run_command(cmd):
    """Run a shell command and return output."""
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        safe_stderr = result.stderr.encode('ascii', 'ignore').decode('ascii')
        print(f"Error: {safe_stderr}")
    return result

def get_db_data(query):
    """Fetch data from the database."""
    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
    conn.close()

def reset_db():
    """Reset the database using the seed SQL file."""
    print("Resetting database...")
    seed_path = Path("utils/test.seed.sql")
    with open(seed_path, "r") as f:
        sql = f.read()
    
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        # Drop tables in reverse order of dependencies
        cur.execute("DROP TABLE IF EXISTS overflow_test CASCADE")
        cur.execute("DROP TABLE IF EXISTS consistency_test CASCADE")
        cur.execute("DROP TABLE IF EXISTS strategy_complex_test CASCADE")
        cur.execute("DROP TABLE IF EXISTS profiles CASCADE")
        cur.execute("DROP TABLE IF EXISTS orders CASCADE")
        cur.execute("DROP TABLE IF EXISTS users CASCADE")
        cur.execute(sql)
    conn.close()

def verify_cli():
    print("=== Starting Comprehensive CLI Verification ===\n")
    
    reset_db()

    # 1. Create a comprehensive config for verification
    config_path = Path("verify_config.yaml")
    config_data = {
        "seed": 42,
        "tables": {
            "users": {
                "username": "fake:username",
                "email": {
                    "strategy": "fake:email",
                    "consistency_group": "user_emails"
                },
                "phone": "fake:phone",
                "date_of_birth": "fake:date",
                "account_balance": "fake:decimal",
                "updated_at": "fake:datetime"
            },
            "orders": {
                "order_total": "fake:number",
                "tax_amount": "fake:decimal",
                "status": "hash"
            },
            "profiles": {
                "bio": "fake:text",
                "age": "fake:int",
                "height": "fake:float",
                "weight": "fake:float"
            },
            "strategy_complex_test": {
                "h_text": "hash",
                "f_email": {
                    "strategy": "fake:email",
                    "consistency_group": "user_emails"
                },
                "f_name": "fake:name",
                "f_first_name": "fake:first_name",
                "f_last_name": "fake:last_name",
                "f_phone": "fake:phone",
                "f_address": "fake:address",
                "f_company": "fake:company",
                "f_text": "fake:text",
                "f_city": "fake:city",
                "f_country": "fake:country",
                "f_postcode": "fake:postcode",
                "f_street_address": "fake:street_address",
                "f_job": "fake:job",
                "f_url": "fake:url",
                "f_username": "fake:username",
                "f_uuid": "fake:uuid",
                "f_int": "fake:int",
                "f_number": "fake:number",
                "f_float": "fake:float",
                "f_decimal": "fake:decimal",
                "f_date": "fake:date",
                "f_datetime": "fake:datetime",
                "s_null": "null",
                "s_preserve": "preserve"
            },
            "overflow_test": {
                "s_int": "fake:int",
                "i_int": "fake:int"
            }
        }
    }
    
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    try:
        # 2. Capture original data for comparison
        print("Fetching original data...")
        orig_all_data = {}
        for table_name in config_data["tables"]:
            orig_all_data[table_name] = get_db_data(f"SELECT * FROM {table_name} ORDER BY id")

        # 3. Run the CLI
        print("Running pg-obfuscate...")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        res = run_command(["pg-obfuscate", "run", "--config", str(config_path), "--db-url", DB_URL, "--force"])
        
        if res.returncode != 0:
            print("CLI failed to execute!")
            return

        # 4. Fetch obfuscated data
        print("Fetching obfuscated data...")
        new_all_data = {}
        for table_name in config_data["tables"]:
            new_all_data[table_name] = get_db_data(f"SELECT * FROM {table_name} ORDER BY id")

        # 5. Verifications
        print("\n--- Validation Results ---")
        
        # Helper to compare rows
        def validate_strategy(col, strat_config, orig_list, new_list):
            ok = True
            strategy = strat_config["strategy"] if isinstance(strat_config, dict) else strat_config
            for o, n in zip(orig_list, new_list):
                o_val = o.get(col)
                n_val = n.get(col)
                
                if strategy == "null":
                    if n_val is not None:
                        print(f"  [FAIL] {col} (null): expected NULL, got {n_val}")
                        ok = False
                elif strategy == "preserve":
                    if n_val != o_val:
                        print(f"  [FAIL] {col} (preserve): expected {o_val}, got {n_val}")
                        ok = False
                elif strategy == "hash" or strategy.startswith("fake"):
                    if o_val is not None and n_val == o_val:
                        print(f"  [FAIL] {col} ({strategy}): value did not change from '{o_val}'")
                        ok = False
                    if n_val is None and o_val is not None:
                        print(f"  [FAIL] {col} ({strategy}): value became NULL unexpectedly")
                        ok = False
            return ok

        # Check all tables in config
        all_ok = True
        for table_name, columns in config_data["tables"].items():
            if table_name == "overflow_test": continue # Validated separately
            for col, strat in columns.items():
                if not validate_strategy(col, strat, orig_all_data[table_name], new_all_data[table_name]):
                    all_ok = False
        print(f"[OK] All strategies across all tables verified: {all_ok}")

        # Verify cross-table consistency (users.email vs strategy_complex_test.f_email)
        print("Verifying Cross-table Consistency (users.email == strategy_complex_test.f_email)...")
        # In seed: users.id=1 has email 'alice@example.com'. strategy_complex_test.id=1 has f_email 'alice@example.com'.
        email1 = next(r["email"] for r in new_all_data["users"] if r["id"] == 1)
        email2 = next(r["f_email"] for r in new_all_data["strategy_complex_test"] if r["id"] == 1)
        
        cross_consistency_ok = (email1 == email2)
        if not cross_consistency_ok:
            print(f"  [FAIL] Cross-table consistency mismatch: {email1} != {email2}")
        print(f"[OK] Cross-table Consistency Groups verified: {cross_consistency_ok}")

        # Verify overflow protection (SMALLINT)
        overflow_ok = True
        for row in new_all_data["overflow_test"]:
            if row['s_int'] < -32768 or row['s_int'] > 32767:
                print(f"  [FAIL] s_int (SMALLINT) overflow: {row['s_int']}")
                overflow_ok = False
            if row['i_int'] < -2147483648 or row['i_int'] > 2147483647:
                print(f"  [FAIL] i_int (INTEGER) overflow: {row['i_int']}")
                overflow_ok = False
        print(f"[OK] Integer overflow protection verified: {overflow_ok}")

        # 6. Verify Determinism
        print("\nVerifying Determinism (Run #2)...")
        reset_db()
        run_command(["pg-obfuscate", "run", "--config", str(config_path), "--db-url", DB_URL, "--force"])
        run2_complex = get_db_data("SELECT * FROM strategy_complex_test ORDER BY id")
        
        determinism_ok = True
        for r1, r2 in zip(new_all_data["strategy_complex_test"], run2_complex):
            for col in r1:
                if r1[col] != r2[col]:
                    print(f"  [FAIL] Determinism mismatch in {col} ID {r1['id']}: Run1='{r1[col]}' Run2='{r2[col]}'")
                    determinism_ok = False
        print(f"[OK] Determinism preserved (Run 1 == Run 2): {determinism_ok}")

        # 7. Verify Consistency Groups
        print("\nVerifying Consistency Groups...")
        config_data["tables"]["consistency_test"] = {
            "col1": {"strategy": "fake:name", "consistency_group": "names"},
            "col2": {"strategy": "fake:name", "consistency_group": "names"}
        }
        # Create consistency_test table
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE consistency_test (id SERIAL PRIMARY KEY, col1 TEXT, col2 TEXT)")
            cur.execute("INSERT INTO consistency_test (col1, col2) VALUES ('Alice', 'Alice'), ('Bob', 'Bob'), ('Charlie', 'Charlie')")
        conn.close()

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
            
        run_command(["pg-obfuscate", "run", "--config", str(config_path), "--db-url", DB_URL, "--force"])
        
        consist_data = get_db_data("SELECT * FROM consistency_test ORDER BY id")
        consistency_ok = all(r["col1"] == r["col2"] for r in consist_data)
        print(f"[OK] Consistency Groups verified (col1 == col2): {consistency_ok}")

    finally:
        if config_path.exists():
            os.remove(config_path)

if __name__ == "__main__":
    verify_cli()
