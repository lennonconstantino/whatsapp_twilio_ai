#!/bin/bash

ENV_FILE=".env"

# Verificar se o arquivo .env existe
if [ ! -f "$ENV_FILE" ]; then
    echo "Erro: Arquivo $ENV_FILE não encontrado."
    exit 1
fi

# Converter o parâmetro para minúsculas
ACTION=$(echo "$1" | tr '[:upper:]' '[:lower:]')

if [ "$ACTION" == "on" ] || [ "$ACTION" == "true" ]; then
    # Ativar fake sender
    # Verifica se a variável já existe no arquivo
    if grep -q "^API_USE_FAKE_SENDER=" "$ENV_FILE"; then
        sed -i '' 's/^API_USE_FAKE_SENDER=.*/API_USE_FAKE_SENDER=True/' "$ENV_FILE"
    else
        echo "API_USE_FAKE_SENDER=True" >> "$ENV_FILE"
    fi
    echo "✅ Ambiente Fake ATIVADO (API_USE_FAKE_SENDER=True)"
    
elif [ "$ACTION" == "off" ] || [ "$ACTION" == "false" ]; then
    # Desativar fake sender
    if grep -q "^API_USE_FAKE_SENDER=" "$ENV_FILE"; then
        sed -i '' 's/^API_USE_FAKE_SENDER=.*/API_USE_FAKE_SENDER=False/' "$ENV_FILE"
    else
        echo "API_USE_FAKE_SENDER=False" >> "$ENV_FILE"
    fi
    echo "🚫 Ambiente Fake DESATIVADO (API_USE_FAKE_SENDER=False)"
    
else
    echo "Uso: ./fake_environment.sh [on|off]"
    echo "  on  : Ativa o API_USE_FAKE_SENDER"
    echo "  off : Desativa o API_USE_FAKE_SENDER"
    exit 1
fi
