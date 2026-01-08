# Conversation Manager Module

Módulo Python para gestão de conversas de WhatsApp e outros canais com integração de agentes de IA.

## Arquitetura

O módulo segue uma arquitetura em camadas:

- **entity**: Definição das entidades do domínio (Conversation, Message)
- **repository**: Camada de acesso a dados (Supabase/PostgreSQL)
- **service**: Lógica de negócio e orquestração
- **view**: Interfaces e DTOs para APIs
- **config**: Configurações da aplicação
- **seeds**: Dados iniciais para desenvolvimento
- **scripts**: Scripts SQL para setup do banco

## Funcionalidades

- ✅ Gestão completa do ciclo de vida de conversas
- ✅ Controle de estados com transições validadas
- ✅ Detecção inteligente de intenção de encerramento
- ✅ Expiração automática de conversas inativas
- ✅ Suporte a múltiplos tipos de mensagens
- ✅ Background jobs para manutenção

## Requisitos

- Python 3.10+
- PostgreSQL (Supabase)
- supabase-py
- pydantic

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração

Configure as variáveis de ambiente no arquivo `.env`:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
DATABASE_SCHEMA=conversations
CONVERSATION_EXPIRY_HOURS=24
IDLE_TIMEOUT_MINUTES=30
```

## Setup do Banco de Dados

```bash
# Executar scripts SQL
python -m conversation_manager.scripts.setup_database
```

## Seeds

```bash
# Carregar dados fake para desenvolvimento
python -m conversation_manager.seeds.load_seeds
```
