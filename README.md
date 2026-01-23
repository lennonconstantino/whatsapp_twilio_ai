# WhatsApp Twilio AI

> Plataforma Enterprise de Automação de Conversas com IA via WhatsApp Business e Twilio.

![Build Status](https://img.shields.io/badge/build-passing-brightgreen) ![Version](https://img.shields.io/badge/version-v3.0-blue) ![Python](https://img.shields.io/badge/python-3.12%2B-blue) ![License](https://img.shields.io/badge/license-Proprietary-red)

## 📖 Sobre o Projeto

**WhatsApp Twilio AI** é uma plataforma robusta e escalável (SaaS Multi-tenant) projetada para automatizar interações complexas no WhatsApp Business. Utilizando **Inteligência Artificial (LLMs)** e uma arquitetura orientada a eventos, o sistema gerencia conversas, mantém contexto e executa ações de negócio de forma autônoma.

### Principais Funcionalidades
- 🤖 **Agentes de IA Inteligentes**: Integração com OpenAI/LangChain para compreensão de linguagem natural.
- 🏢 **Multi-Tenant**: Suporte isolado para múltiplas organizações e contas Twilio.
- ⚡ **Alta Performance**: Processamento assíncrono distribuído com filas (Agnóstico: BullMQ, SQS, SQLite).
- 🔄 **Resiliência**: Mecanismos de Fallback, Idempotência e Recuperação de Falhas.
- 📊 **Gestão de Ciclo de Vida**: Máquina de estados completa para gerenciar conversas (Timeout, Expiração, Encerramento).

## 🚀 Tecnologias Utilizadas

- **Core**: Python 3.12+, FastAPI, Pydantic (Strict Typing).
- **Arquitetura**: Dependency Injection, Clean Architecture, Repository Pattern.
- **Banco de Dados**: PostgreSQL (via Supabase).
- **Integrações**: Twilio API, OpenAI API, LangChain.
- **Mensageria/Filas**: Abstração `QueueService` (Suporte a Redis/BullMQ e AWS SQS).
- **DevOps**: Docker, Makefile.

## 📋 Pré-requisitos

Para executar este projeto localmente, você precisará de:

- **Python 3.12+**
- **Docker & Docker Compose** (para Redis e serviços auxiliares)
- **Conta Supabase** (ou instância Postgres local)
- **Conta Twilio** (para webhooks e envio de mensagens)
- **Ngrok** (para expor o webhook localmente)

## 🔧 Instalação

1. **Clone o repositório**
   ```bash
   git clone https://github.com/seu-usuario/whatsapp_twilio_ai.git
   cd whatsapp_twilio_ai
   ```

2. **Configure o ambiente virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou
   .\venv\Scripts\activate  # Windows
   ```

3. **Instale as dependências**
   ```bash
   make install
   # ou
   pip install -r requirements.txt
   ```

4. **Configure as Variáveis de Ambiente**
   Copie o exemplo e preencha com suas credenciais:
   ```bash
   cp .env.example .env
   ```
   > **Nota**: Preencha chaves críticas como `SUPABASE_URL`, `SUPABASE_KEY`, `TWILIO_ACCOUNT_SID`, `OPENAI_API_KEY`.

## ⚡ Como Usar

### Comandos Úteis (Makefile)

O projeto inclui um `Makefile` para facilitar operações comuns:

- **Iniciar a Aplicação**:
  ```bash
  make run
  ```
  O servidor estará disponível em `http://localhost:8000`.

- **Executar Migrations**:
  ```bash
  make migrate
  ```

- **Popular Banco de Dados (Seed)**:
  ```bash
  make seed
  ```

- **Rodar Testes**:
  ```bash
  make test
  ```

### Exemplo de Uso Local (Webhook)

1. Inicie o servidor: `make run`
2. Exponha a porta 8000 via Ngrok: `ngrok http 8000`
3. Configure a URL do webhook no Console do Twilio: `https://seu-ngrok.ngrok-free.app/api/v1/twilio/webhook`
4. Envie uma mensagem para o número do WhatsApp configurado.

## 📚 Documentação Adicional

A documentação técnica detalhada encontra-se na pasta `docs/v3/`:

- 📐 **[Arquitetura do Sistema](docs/v3/architecture.md)**
  Detalhes sobre padrões de design, fluxo de dados e decisões arquiteturais.

- 🔧 **[Últimas Correções](docs/v3/last_corrections.md)**
  Histórico recente de refatorações, correções de segurança e melhorias de performance.

- 📊 **[Diagramas](docs/v3/diagrams.md)**
  Representações visuais da arquitetura, ciclo de vida e fluxos (Mermaid).

- 📝 **[Resumo do Projeto](docs/v3/project_summary.md)**
  Visão geral executiva e status de maturidade do projeto.

## 📂 Estrutura de Pastas

```
src/
├── api/          # Rotas e Controllers (FastAPI)
├── core/         # Infraestrutura base (Config, DB, Queue, DI)
├── modules/      # Domínios de Negócio
│   ├── ai/             # Motores de Inteligência e Agentes
│   ├── channels/       # Integração Twilio/WhatsApp
│   ├── conversation/   # Gestão de Estado e Mensagens
│   └── identity/       # Gestão de Tenants, Usuários e Permissões
└── main.py       # Ponto de entrada da aplicação
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, siga estes passos:

1. Faça um Fork do projeto.
2. Crie uma Branch para sua Feature (`git checkout -b feature/MinhaFeature`).
3. Commit suas mudanças (`git commit -m 'Add: Minha nova feature'`).
4. Push para a Branch (`git push origin feature/MinhaFeature`).
5. Abra um Pull Request.

**Guia de Estilo**: O projeto utiliza `black`, `isort` e `flake8`. Execute `make format` e `make lint` antes de submeter.

## 📄 Licença

Este projeto é **Proprietário**. Todos os direitos reservados.
Consulte o arquivo `LICENSE` (se disponível) ou contate os autores para permissões de uso.

## 📞 Contato / Autores

- **Lennon** - Arquiteto de Software e Desenvolvedor Líder
