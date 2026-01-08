import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def run_migrations():
    database_url = os.getenv("DATABASE_URL")
    migrations_dir = Path("migrations")
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    # Pega todos os arquivos .sql ordenados
    sql_files = sorted(migrations_dir.glob("*.sql"))
    
    for sql_file in sql_files:
        print(f"Running {sql_file.name}...")
        with open(sql_file, "r") as f:
            sql = f.read()
            cursor.execute(sql)
        conn.commit()
        print(f"✓ {sql_file.name} executed successfully")
    
    cursor.close()
    conn.close()
    print("All migrations completed!")

if __name__ == "__main__":
    run_migrations()
