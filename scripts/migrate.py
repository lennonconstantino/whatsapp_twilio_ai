import os
import argparse
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def run_migrations(specific_file=None):
    database_url = os.getenv("DATABASE_URL")
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    if specific_file:
        file_path = Path(specific_file)
        if not file_path.exists():
            print(f"Error: File {file_path} does not exist.")
            return
        sql_files = [file_path]
        print(f"Running specific migration: {file_path.name}...")
    else:
        migrations_dir = Path("migrations")
        # Pega todos os arquivos .sql ordenados
        sql_files = sorted(migrations_dir.glob("*.sql"))
        print(f"Running all migrations from {migrations_dir}...")

    for sql_file in sql_files:
        print(f"Running {sql_file.name}...")
        with open(sql_file, "r") as f:
            sql = f.read()
            cursor.execute(sql)
        conn.commit()
        print(f"✓ {sql_file.name} executed successfully")

    cursor.close()
    conn.close()
    print("Migration(s) completed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("file", nargs="?", help="Specific migration file path to run (optional)")
    args = parser.parse_args()

    run_migrations(args.file)
