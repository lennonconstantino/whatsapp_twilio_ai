
import os
import sys
import psycopg2
from tabulate import tabulate
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

# Load .env file
load_dotenv()

def check_database():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Erro: DATABASE_URL não definida no .env")
        return

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        print("\n--- 1. Verificando Schemas ---")
        cursor.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema';")
        schemas = cursor.fetchall()
        print(tabulate(schemas, headers=["Schema Name"], tablefmt="psql"))

        print("\n--- 2. Verificando Tabelas no schema 'app' ---")
        cursor.execute("SELECT table_name, table_schema FROM information_schema.tables WHERE table_schema = 'app';")
        tables = cursor.fetchall()
        if not tables:
            print("⚠️  NENHUMA tabela encontrada no schema 'app'!")
        else:
            print(tabulate(tables, headers=["Table", "Schema"], tablefmt="psql"))

        print("\n--- 3. Verificando Permissões (Roles) ---")
        # Check usage on schema app
        cursor.execute("""
            SELECT grantee, privilege_type 
            FROM information_schema.role_usage_grants 
            WHERE object_schema = 'app';
        """)
        perms = cursor.fetchall()
        print("Permissões de USAGE no schema 'app':")
        print(tabulate(perms, headers=["Role", "Privilege"], tablefmt="psql"))

        print("\n--- 4. Verificando Configuração do Authenticator ---")
        cursor.execute("SELECT rolname, rolconfig FROM pg_roles WHERE rolname = 'authenticator';")
        config = cursor.fetchall()
        print(tabulate(config, headers=["Role", "Config"], tablefmt="psql"))

    except Exception as e:
        print(f"Erro ao conectar/consultar: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    check_database()
