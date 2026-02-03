
import os
import sys
import psycopg2
from dotenv import load_dotenv
from tabulate import tabulate

sys.path.append(os.getcwd())
load_dotenv()

def check_ai_results_table():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Erro: DATABASE_URL não definida no .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("\n--- Checking app.ai_results structure ---")
        cursor.execute("""
            SELECT column_name, data_type, udt_name, column_default
            FROM information_schema.columns 
            WHERE table_schema = 'app' AND table_name = 'ai_results';
        """)
        
        columns = cursor.fetchall()
        if columns:
            print(tabulate(columns, headers=["Column", "Type", "UDT", "Default"], tablefmt="psql"))
        else:
            print("Table app.ai_results NOT FOUND.")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    check_ai_results_table()
