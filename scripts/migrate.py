import os
import argparse
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def run_migrations(path_arg=None, dry_run=False):
    database_url = os.getenv("DATABASE_URL")
    
    # Connect to DB only if needed or to verify connection? 
    # Let's verify connection even in dry-run to ensure env is correct
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    # Determine target path
    # If path_arg is provided, use it. Otherwise default to "migrations" directory
    target_path = Path(path_arg) if path_arg else Path("migrations")

    if not target_path.exists():
        print(f"Error: Path {target_path} does not exist.")
        cursor.close()
        conn.close()
        return

    sql_files = []
    
    if target_path.is_file():
        # Case 1: Specific file
        if target_path.suffix != '.sql':
            print(f"Warning: File {target_path} does not appear to be a SQL file.")
        sql_files = [target_path]
        print(f"Running specific migration: {target_path.name}...")
        
    elif target_path.is_dir():
        # Case 2: Directory
        # Get all .sql files sorted by name
        sql_files = sorted(target_path.glob("*.sql"))
        print(f"Running all migrations from {target_path}...")
        
        if not sql_files:
            print(f"No .sql files found in {target_path}")
            cursor.close()
            conn.close()
            return

    if dry_run:
        print("\n--- DRY RUN MODE: No changes will be applied ---\n")

    for sql_file in sql_files:
        if dry_run:
            print(f"[DRY-RUN] Would execute: {sql_file.name}")
            continue

        print(f"Running {sql_file.name}...")
        try:
            with open(sql_file, "r") as f:
                sql = f.read()
                cursor.execute(sql)
            conn.commit()
            print(f"✓ {sql_file.name} executed successfully")
        except Exception as e:
            conn.rollback()
            print(f"✗ Error executing {sql_file.name}: {e}")
            # Stop on error? Usually yes for migrations.
            break

    cursor.close()
    conn.close()
    
    if dry_run:
        print("\n--- DRY RUN COMPLETED ---")
    else:
        print("Migration(s) completed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("path", nargs="?", help="Specific migration file path or directory to run (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration execution without applying changes")
    args = parser.parse_args()

    run_migrations(args.path, args.dry_run)
