import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def run_migration():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set")
        return

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        with open("migrations/003_add_version_column.sql", "r") as f:
            sql = f.read()
            print(f"Executing: {sql}")
            cursor.execute(sql)
            
        conn.commit()
        print("Migration 003 executed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    run_migration()
