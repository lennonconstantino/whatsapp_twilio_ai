
import os
import sys
import psycopg2
from dotenv import load_dotenv
from tabulate import tabulate

sys.path.append(os.getcwd())
load_dotenv()

def check_function_exists():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Erro: DATABASE_URL não definida no .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("\n--- Checking for generate_ulid function ---")
        cursor.execute("""
            SELECT n.nspname as schema, p.proname as function_name, pg_get_function_arguments(p.oid) as args
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE p.proname = 'generate_ulid';
        """)
        
        functions = cursor.fetchall()
        if functions:
            print(tabulate(functions, headers=["Schema", "Function", "Args"], tablefmt="psql"))
        else:
            print("Function 'generate_ulid' NOT FOUND in any schema.")
            
        print("\n--- Checking search_path ---")
        cursor.execute("SHOW search_path;")
        print(cursor.fetchone()[0])

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    check_function_exists()
