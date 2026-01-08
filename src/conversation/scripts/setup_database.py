"""
Script para setup do banco de dados
"""
import sys
from pathlib import Path
from supabase import create_client
import psycopg2
from psycopg2 import sql

# Adicionar o diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from conversation_manager.config.settings import settings


def execute_sql_file(connection, file_path: Path):
    """
    Executa um arquivo SQL.
    
    Args:
        connection: Conexão com o banco
        file_path: Caminho do arquivo SQL
    """
    print(f"\nExecutando {file_path.name}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    try:
        cursor = connection.cursor()
        cursor.execute(sql_content)
        connection.commit()
        cursor.close()
        print(f"✓ {file_path.name} executado com sucesso")
        return True
    except Exception as e:
        print(f"✗ Erro ao executar {file_path.name}: {e}")
        connection.rollback()
        return False


def get_postgres_connection():
    """
    Cria uma conexão PostgreSQL a partir da URL do Supabase.
    """
    # Extrair informações da URL do Supabase
    # Formato: https://<project-ref>.supabase.co
    url = settings.supabase_url
    
    # Para Supabase, normalmente a conexão PostgreSQL usa:
    # Host: db.<project-ref>.supabase.co
    # Port: 5432
    # Database: postgres
    # User: postgres
    # Password: sua senha de projeto
    
    print("\n" + "=" * 60)
    print("CONFIGURAÇÃO DO BANCO DE DADOS")
    print("=" * 60)
    print("\nPara conectar ao PostgreSQL do Supabase, você precisa:")
    print("1. Host: db.<seu-projeto>.supabase.co")
    print("2. Port: 5432")
    print("3. Database: postgres")
    print("4. User: postgres")
    print("5. Password: sua senha de projeto do Supabase")
    print("\nVocê pode encontrar essas informações em:")
    print("Supabase Dashboard > Project Settings > Database > Connection string")
    print("=" * 60)
    
    # Solicitar informações do usuário
    host = input("\nHost (ex: db.xxxxx.supabase.co): ").strip()
    port = input("Port [5432]: ").strip() or "5432"
    database = input("Database [postgres]: ").strip() or "postgres"
    user = input("User [postgres]: ").strip() or "postgres"
    password = input("Password: ").strip()
    
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print("\n✓ Conexão estabelecida com sucesso!")
        return connection
    except Exception as e:
        print(f"\n✗ Erro ao conectar: {e}")
        return None


def main():
    """Função principal"""
    print("\n" + "=" * 60)
    print("SETUP DO BANCO DE DADOS - CONVERSATION MANAGER")
    print("=" * 60)
    
    # Conectar ao banco
    connection = get_postgres_connection()
    if not connection:
        print("\n✗ Não foi possível conectar ao banco de dados")
        return
    
    # Diretório de scripts
    scripts_dir = Path(__file__).parent
    sql_files = sorted(scripts_dir.glob("*.sql"))
    
    if not sql_files:
        print("\n⚠ Nenhum arquivo SQL encontrado")
        return
    
    print(f"\n{len(sql_files)} script(s) SQL encontrado(s):")
    for f in sql_files:
        print(f"  - {f.name}")
    
    # Executar scripts
    print("\nExecutando scripts SQL...")
    success_count = 0
    
    for sql_file in sql_files:
        if execute_sql_file(connection, sql_file):
            success_count += 1
    
    # Fechar conexão
    connection.close()
    
    # Resumo
    print("\n" + "=" * 60)
    if success_count == len(sql_files):
        print("✓ SETUP CONCLUÍDO COM SUCESSO!")
    else:
        print(f"⚠ SETUP PARCIAL: {success_count}/{len(sql_files)} scripts executados")
    print("=" * 60)
    
    if success_count == len(sql_files):
        print("\nPróximos passos:")
        print("1. Configure o arquivo .env com suas credenciais")
        print("2. Execute: python -m conversation_manager.seeds.load_seeds")
        print("   para carregar dados fake de exemplo")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Setup cancelado pelo usuário")
    except Exception as e:
        print(f"\n✗ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
