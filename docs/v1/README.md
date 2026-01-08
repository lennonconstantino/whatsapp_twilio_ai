# Owner Project

Sistema multi-tenant de gerenciamento de conversas com integração Twilio, construído com Python, FastAPI e Supabase PostgreSQL.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Funcionalidades](#funcionalidades)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [API Endpoints](#api-endpoints)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Desenvolvimento](#desenvolvimento)

## 🎯 Visão Geral

O Owner Project é uma plataforma de gerenciamento de conversas que permite:

- **Multi-tenancy**: Isolamento completo de dados entre diferentes organizações (owners)
- **Integração Twilio**: Envio e recebimento de mensagens via WhatsApp, SMS, etc.
- **Detecção Inteligente de Encerramento**: Sistema de IA para detectar quando usuários querem encerrar conversas
- **Gestão de Features**: Sistema flexível para habilitar funcionalidades por tenant
- **Ciclo de Vida Completo**: Gerenciamento de conversas com estados, expiração e timeouts

## 🏗️ Arquitetura

### Diagrama de Entidades

```
owners (Tenants)
 ├── users (Staff do tenant)
 ├── features (Funcionalidades habilitadas)
 ├── twilio_accounts (Credenciais Twilio)
 └── conversations (Histórico de conversas)
      └── messages (Mensagens da conversa)
           └── ai_results (Resultados de processamento IA)
```

### Stack Tecnológico

- **Backend**: Python 3.9+, FastAPI
- **Database**: Supabase (PostgreSQL)
- **Messaging**: Twilio API
- **Logging**: Structlog
- **Testing**: Pytest

## ✨ Funcionalidades

### Core

1. **Gerenciamento de Conversas**
   - Criação automática ou busca de conversas ativas
   - Estados de conversa (pending, progress, closed, etc.)
   - Expiração e timeout automáticos
   - Extensão de tempo de conversa

2. **Detecção de Encerramento**
   - Análise de palavras-chave contextuais
   - Padrões de mensagens
   - Sinais de metadata
   - Score de confiança para tomada de decisão

3. **Integração Twilio**
   - Webhook para recebimento de mensagens
   - Envio de mensagens
   - Status callbacks
   - Suporte a múltiplos tipos de mídia

4. **Multi-tenant**
   - Isolamento completo de dados
   - Configurações por tenant
   - Features habilitáveis individualmente

## 🚀 Instalação

### Pré-requisitos

- Python 3.9 ou superior
- PostgreSQL (via Supabase)
- Conta Twilio (opcional, para integração)

### Passos

1. **Clone o repositório**

```bash
git clone <repository-url>
cd owner-project
```

2. **Crie um ambiente virtual**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Instale as dependências**

```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente**

```bash
cp .env.example .env
# Edite .env com suas credenciais
```

## ⚙️ Configuração

### Variáveis de Ambiente

Edite o arquivo `.env` com suas configurações:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/owner_db

# Twilio (opcional)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=True

# Conversation Settings
CONVERSATION_EXPIRATION_MINUTES=1440
CONVERSATION_IDLE_TIMEOUT_MINUTES=60
```

### Banco de Dados

1. **Execute as migrações**

```bash
# No Supabase Dashboard, execute o SQL em:
# migrations/001_initial_schema.sql
```

2. **Popule dados iniciais**

```bash
python scripts/seed.py
```

## 📖 Uso

### Iniciar o Servidor

```bash
# Modo desenvolvimento
python -m src.main

# Ou com uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Exemplos de Uso

#### 1. Criar uma Conversa

```python
import requests

response = requests.post(
    "http://localhost:8000/conversations/",
    json={
        "owner_id": 1,
        "from_number": "+5511988887777",
        "to_number": "+5511999998888",
        "channel": "whatsapp"
    }
)

conversation = response.json()
print(f"Conversa criada: {conversation['conv_id']}")
```

#### 2. Adicionar Mensagem

```python
response = requests.post(
    f"http://localhost:8000/conversations/{conv_id}/messages",
    json={
        "conv_id": conv_id,
        "from_number": "+5511988887777",
        "to_number": "+5511999998888",
        "body": "Olá, preciso de ajuda!",
        "direction": "inbound",
        "message_owner": "user"
    }
)

message = response.json()
```

#### 3. Listar Conversas Ativas

```python
response = requests.get(
    "http://localhost:8000/conversations/",
    params={"owner_id": 1, "limit": 50}
)

conversations = response.json()
```

## 🔌 API Endpoints

### Conversas

- `POST /conversations/` - Criar ou buscar conversa ativa
- `GET /conversations/{conv_id}` - Buscar conversa por ID
- `GET /conversations/` - Listar conversas ativas
- `GET /conversations/{conv_id}/messages` - Listar mensagens
- `POST /conversations/{conv_id}/messages` - Adicionar mensagem
- `POST /conversations/{conv_id}/close` - Fechar conversa
- `POST /conversations/{conv_id}/extend` - Estender expiração

### Webhooks Twilio

- `POST /webhooks/twilio/inbound` - Receber mensagens
- `POST /webhooks/twilio/status` - Status de mensagens
- `GET /webhooks/twilio/health` - Health check

### Geral

- `GET /` - Informações da API
- `GET /health` - Health check

## 📁 Estrutura do Projeto

```
owner-project/
├── src/
│   ├── api/                  # Rotas da API
│   │   ├── conversations.py
│   │   └── webhooks.py
│   ├── config/              # Configurações
│   │   └── settings.py
│   ├── models/              # Modelos de dados
│   │   ├── domain.py
│   │   └── enums.py
│   ├── repositories/        # Camada de persistência
│   │   ├── base.py
│   │   ├── conversation_repository.py
│   │   ├── message_repository.py
│   │   ├── owner_repository.py
│   │   └── ...
│   ├── services/            # Lógica de negócio
│   │   ├── closure_detector.py
│   │   ├── conversation_service.py
│   │   └── twilio_service.py
│   ├── utils/               # Utilitários
│   │   ├── database.py
│   │   └── logging.py
│   └── main.py              # Aplicação principal
├── migrations/              # Migrações SQL
│   └── 001_initial_schema.sql
├── scripts/                 # Scripts utilitários
│   └── seed.py
├── tests/                   # Testes
├── .env.example            # Exemplo de variáveis de ambiente
├── requirements.txt        # Dependências
└── README.md              # Este arquivo
```

## 🔧 Desenvolvimento

### Executar Testes

```bash
pytest tests/ -v --cov=src
```

### Linting

```bash
# Black (formatação)
black src/ tests/

# Flake8 (linting)
flake8 src/ tests/

# MyPy (type checking)
mypy src/
```

### Adicionar Nova Feature

1. Crie o modelo em `src/models/`
2. Crie o repository em `src/repositories/`
3. Crie o service em `src/services/`
4. Adicione rotas em `src/api/`
5. Atualize a documentação

## 📝 Closure Detector

O sistema de detecção de encerramento usa múltiplos fatores:

### Palavras-chave

Por padrão, detecta: `tchau`, `obrigado`, `valeu`, `até logo`, `até mais`, `até breve`, `bye`, `thanks`

### Padrões de Mensagens

- Respostas curtas após resposta da IA
- Confirmações positivas (sim, ok, certo)
- Mensagem final após sequência de respostas

### Contexto

- Objetivo alcançado (`goal_achieved: true`)
- Sem ações pendentes (`pending_actions: []`)
- Flag de conclusão (`can_close: true`)

### Score de Confiança

- `< 0.6`: Não fecha
- `0.6 - 0.8`: Registra no contexto, aguarda confirmação
- `>= 0.8`: Fecha automaticamente

## 🔒 Segurança

- Row Level Security (RLS) habilitado em todas as tabelas
- Isolamento de dados por owner_id
- Validação de webhook signatures do Twilio
- Sanitização de inputs

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT.

## 📞 Suporte

Para suporte, abra uma issue no GitHub ou entre em contato com a equipe de desenvolvimento.
