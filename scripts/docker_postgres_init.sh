#!/bin/bash
set -e

# Script de inicialização para Docker (substituto do migrate_postgres.sh que usa Python)
# Este script usa psql diretamente para ser compatível com a imagem postgres alpine/debian

echo "Iniciando migrações personalizadas..."

# Função auxiliar para rodar psql
run_sql() {
    local file="$1"
    if [ -f "$file" ]; then
        echo "Running $file..."
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$file"
    else
        echo "Warning: File $file not found, skipping."
    fi
}

# Caminho onde as migrações serão montadas
MIGRATIONS_DIR="/opt/migrations"

# Executa na mesma ordem do scripts/migrate_postgres.sh

# 1. Limpeza/Setup inicial
run_sql "$MIGRATIONS_DIR/000_drop_database.sql"

# 2. Roles (iterar sobre diretório)
# O shell expande em ordem alfabética por padrão
if [ -d "$MIGRATIONS_DIR/roles" ]; then
    for f in "$MIGRATIONS_DIR/roles"/*.sql; do
        run_sql "$f"
    done
fi

# 3. Core Migrations
run_sql "$MIGRATIONS_DIR/001_create_extensions.sql"
run_sql "$MIGRATIONS_DIR/002_create_core_functions.sql"
run_sql "$MIGRATIONS_DIR/003_create_tables.sql"
run_sql "$MIGRATIONS_DIR/004_create_search_functions.sql"
run_sql "$MIGRATIONS_DIR/006_usage_examples.sql"
run_sql "$MIGRATIONS_DIR/007_security_policies.sql"
run_sql "$MIGRATIONS_DIR/008_fix_ai_results_id.sql"
run_sql "$MIGRATIONS_DIR/009_saas_multitenant.sql"
run_sql "$MIGRATIONS_DIR/010_register_organization_rpc.sql"
run_sql "$MIGRATIONS_DIR/011_fix_ai_results_feature_fk.sql"
run_sql "$MIGRATIONS_DIR/012_recreate_ai_results.sql"

# 4. Features (iterar sobre diretório)
if [ -d "$MIGRATIONS_DIR/feature" ]; then
    for f in "$MIGRATIONS_DIR/feature"/*.sql; do
        run_sql "$f"
    done
fi

echo "Migrações concluídas com sucesso!"
