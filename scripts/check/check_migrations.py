
import os
import sys
import psycopg2
from dotenv import load_dotenv
from tabulate import tabulate

sys.path.append(os.getcwd())
load_dotenv()

def check_migrations_status():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Erro: DATABASE_URL não definida no .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check if _migrations table exists (or similar)
        # Assuming a table to track migrations, often 'migrations' or 'schema_migrations' or similar in 'app' or 'public'
        
        # First check tables
        cursor.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE '%migration%';
        """)
        tables = cursor.fetchall()
        print("\n--- Migration Tables ---")
        if tables:
            print(tabulate(tables, headers=["Schema", "Table"], tablefmt="psql"))
            
            # If found, query it
            schema, table = tables[0]
            print(f"\n--- Content of {schema}.{table} ---")
            cursor.execute(f"SELECT * FROM {schema}.{table} ORDER BY 1 DESC LIMIT 10;")
            rows = cursor.fetchall()
            if rows:
                # Get column names
                colnames = [desc[0] for desc in cursor.description]
                print(tabulate(rows, headers=colnames, tablefmt="psql"))
            else:
                print("Table is empty.")
        else:
            print("No migration tracking table found.")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    check_migrations_status()
