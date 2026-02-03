
import os
import sys
import psycopg2
from dotenv import load_dotenv
from tabulate import tabulate

sys.path.append(os.getcwd())
load_dotenv()

def check_ai_results_data():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Erro: DATABASE_URL não definida no .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("\n--- Checking app.ai_results data (first 5) ---")
        cursor.execute("SELECT ai_result_id, length(ai_result_id) as len FROM app.ai_results LIMIT 5;")
        
        rows = cursor.fetchall()
        if rows:
            print(tabulate(rows, headers=["ai_result_id", "length"], tablefmt="psql"))
        else:
            print("Table app.ai_results is empty.")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    check_ai_results_data()
