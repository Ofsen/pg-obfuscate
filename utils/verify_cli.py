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
    # Explicitly use utf-8 for capturing output to avoid system encoding issues
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        # If there's an error, print it safely by removing non-ASCII characters if needed
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
        cur.execute("DROP TABLE IF EXISTS profiles CASCADE")
        cur.execute("DROP TABLE IF EXISTS orders CASCADE")
        cur.execute("DROP TABLE IF EXISTS users CASCADE")
        cur.execute(sql)
        # Also ensure status column is wide enough
        cur.execute("ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR(100)")
    conn.close()

def verify_cli():
    print("=== Starting CLI Verification ===\n")
    
    reset_db()

    # 1. Create a specific config for verification
    config_path = Path("verify_config.yaml")
    config_data = {
        "seed": 1337,
        "tables": {
            "users": {
                "username": "fake:username",
                "email": {
                    "strategy": "fake:email",
                    "consistency_group": "user_email"
                }
            },
            "orders": {
                "status": "hash"
            }
        }
    }
    
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    try:
        # 2. Capture original data for comparison
        print("Fetching original data...")
        orig_users = get_db_data("SELECT id, username, email FROM users ORDER BY id")
        orig_orders = get_db_data("SELECT id, status FROM orders ORDER BY id")

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
        new_users = get_db_data("SELECT id, username, email FROM users ORDER BY id")
        new_orders = get_db_data("SELECT id, status FROM orders ORDER BY id")

        # 5. Verifications
        print("\n--- Validation Results ---")
        
        # Verify usernames changed
        username_changed = all(u["username"] != o["username"] for u, o in zip(new_users, orig_users))
        print(f"[OK] Usernames obfuscated: {username_changed}")

        # Verify emails changed
        email_changed = all(u["email"] != o["email"] for u, o in zip(new_users, orig_users))
        print(f"[OK] Emails obfuscated: {email_changed}")

        # Verify status hashed (it might be truncated to 20 chars)
        status_hashed = all(u["status"] != o["status"] for u, o in zip(new_orders, orig_orders))
        print(f"[OK] Order status changed (hashed): {status_hashed}")

        # 6. Verify Determinism (Run again with same config on fresh data)
        print("\nVerifying Determinism (Run #2)...")
        reset_db()
        run_command(["pg-obfuscate", "run", "--config", str(config_path), "--db-url", DB_URL, "--force"])
        run2_users = get_db_data("SELECT id, username, email FROM users ORDER BY id")
        
        determinism_ok = True
        for u1, u2 in zip(new_users, run2_users):
            if u1["username"] != u2["username"]:
                print(f"  FAILED: ID {u1['id']} username Run1='{u1['username']}' Run2='{u2['username']}'")
                determinism_ok = False
                break
        print(f"[OK] Determinism preserved (Run 1 == Run 2): {determinism_ok}")

        # 7. Verify Consistency Groups (Re-run with a shared group)
        print("\nVerifying Consistency Groups...")
        # Add profile.bio to config
        config_data["tables"]["profiles"] = {
            "bio": {
                "strategy": "fake:email",
                "consistency_group": "user_email" # Same group as users.email
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
            
        run_command(["pg-obfuscate", "run", "--config", str(config_path), "--db-url", DB_URL, "--force"])
        
        print("Synchronizing users.email and profiles.bio for consistency test...")
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("UPDATE profiles SET bio = (SELECT email FROM users WHERE users.id = profiles.user_id)")
            conn.commit()
        conn.close()
        
        run_command(["pg-obfuscate", "run", "--config", str(config_path), "--db-url", DB_URL, "--force"])
        
        users_emails = get_db_data("SELECT user_id, email FROM users JOIN profiles ON users.id = profiles.user_id ORDER BY users.id")
        profiles_bios = get_db_data("SELECT user_id, bio FROM profiles ORDER BY user_id")
        
        consistency_ok = all(u["email"] == p["bio"] for u, p in zip(users_emails, profiles_bios))
        print(f"[OK] Consistency Groups verified (Same input + Same group = Same output): {consistency_ok}")

    finally:
        if config_path.exists():
            os.remove(config_path)

if __name__ == "__main__":
    verify_cli()
