# WhatsApp Twilio AI

> Plataforma Enterprise de Automação de Conversas com IA via WhatsApp Business e Twilio.

![Build Status](https://img.shields.io/badge/build-passing-brightgreen) ![Version](https://img.shields.io/badge/version-v4.0-blue) ![Python](https://img.shields.io/badge/python-3.12%2B-blue) ![License](https://img.shields.io/badge/license-Proprietary-red)

## 📖 Sobre o Projeto

**WhatsApp Twilio AI** é uma plataforma robusta e escalável (SaaS Multi-tenant) projetada para automatizar interações complexas no WhatsApp Business. Utilizando **Inteligência Artificial (LLMs)** e uma arquitetura orientada a eventos (Modular Monolith), o sistema gerencia conversas, mantém contexto e executa ações de negócio de forma autônoma.

## 🏗️ Arquitetura do Sistema

### Contexto do Sistema (C4 Level 1)

O diagrama abaixo ilustra o fluxo de interações do sistema com usuários e serviços externos:

```mermaid
graph TB
    %% Atores
    User(["📱 Usuário Final<br/>(WhatsApp Personal)"])
    Owner(["💼 Owner/Admin<br/>(Gestor da Empresa)"])

    %% Sistema Principal
    subgraph Platform ["WhatsApp Twilio AI Platform"]
        System["🤖 Core System<br/>(Modular Monolith)"]
    end

    %% Sistemas Externos
    Twilio["📡 Twilio<br/>(Messaging Channel)"]
    LLM["🧠 LLM Providers<br/>(OpenAI/Groq/Google)"]
    Stripe["💳 Stripe<br/>(Payment Gateway)"]
    Supabase["🗄️ Supabase<br/>(Database & Auth)"]

    %% Relacionamentos
    User -- "Envia mensagem (WhatsApp)" --> Twilio
    Twilio -- "Webhook (JSON)" --> System
    System -- "Responde (API)" --> Twilio
    Twilio -- "Entrega resposta" --> User

    Owner -- "Gerencia Assinatura" --> Stripe
    System -- "Valida Pagamento" --> Stripe

    System -- "Gera Completions/Embeddings" --> LLM
    System -- "Persiste Dados/Logs" --> Supabase

    %% Estilização (C4 Colors)
    classDef person fill:#08427b,stroke:#052e56,color:#fff
    classDef system fill:#1168bd,stroke:#0b4884,color:#fff
    classDef external fill:#999999,stroke:#6b6b6b,color:#fff

    class User,Owner person
    class System system
    class Twilio,LLM,Stripe,Supabase external
```

### Version 5.0
![Arquitetura de Infraestrutura](docs/image/README/arquitetura_infrastructure.png)

### Principais Funcionalidades
- 🤖 **Agentes de IA Inteligentes**: Integração com OpenAI/LangChain, com seleção dinâmica de agentes e memória híbrida (Redis + Vector Store).
- 🏢 **Multi-Tenant**: Suporte isolado para múltiplas organizações e contas Twilio.
- ⚡ **Alta Performance**: Processamento assíncrono distribuído com filas (QueueService unificado) e Webhooks de resposta imediata.
- 🗣️ **Human Handoff**: Mecanismo para transbordo de atendimento para humanos quando a IA não resolve.
- 🔒 **Segurança e Conformidade**: Gestão segura de mídia e downloads isolados.
- 🔄 **Resiliência**: Mecanismos de Fallback, Idempotência e Recuperação de Falhas.
- 📊 **Gestão de Ciclo de Vida**: Máquina de estados completa para gerenciar conversas (Timeout, Expiração, Encerramento).

## 🧩 Módulos do Sistema

O sistema é construído sobre uma arquitetura modular (Modular Monolith), onde cada componente possui responsabilidades bem definidas:

- **[AI Module](src/modules/ai/README.md)**: Núcleo de inteligência que orquestra agentes, processa linguagem natural e gerencia memória híbrida.
- **[Billing Module](src/modules/billing/README.md)**: Gerenciamento completo de planos, assinaturas, controle de quotas e integração com Stripe.
- **[Channels (Twilio)](src/modules/channels/twilio/README.md)**: Gateway de comunicação com WhatsApp via Twilio, processando webhooks e mídia com alta disponibilidade.
- **[Conversation](src/modules/conversation/README.md)**: Gestão do ciclo de vida das conversas, manutenção de contexto e persistência de mensagens.
- **[Core](src/core/readme.md)**: Shared Kernel contendo infraestrutura base, configurações, abstrações de banco de dados e sistema de filas.
- **[Identity](src/modules/identity/README.md)**: Gestão de identidade, autenticação, controle de acesso (RBAC) e registro de organizações (Tenants).

## 🚀 Tecnologias Utilizadas

- **Core**: Python 3.12+, FastAPI, Pydantic (Strict Typing), Dependency Injection (Container).
- **Arquitetura**: Modular Monolith, Clean Architecture, Repository Pattern.
- **Banco de Dados**: PostgreSQL (via Supabase/PostgREST).
- **Integrações**: Twilio API (Inbound/Outbound), OpenAI API, LangChain.
- **Mensageria/Filas**: BullMQ (Redis) via QueueService unificado.
- **DevOps**: Docker, Makefile, Scripts de verificação de ambiente.

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

5. **Verifique o Ambiente**
   Execute o script de verificação para garantir que tudo está configurado corretamente:
   ```bash
   make check-env
   ```

## ⚡ Como Usar

### Comandos Úteis (Makefile)

O projeto inclui um `Makefile` para facilitar operações comuns:

- **Iniciar a Aplicação**:
  ```bash
  make run
  ```
  O servidor estará disponível em `http://localhost:8000`.
  > **Nota**: Este comando agora verifica se o worker está rodando.

- **Iniciar Infraestrutura de Background (Obrigatório)**:
  Para o funcionamento correto do sistema, você deve rodar os workers e o scheduler em terminais separados:

  **Terminal 1 (Worker de Filas):**
  ```bash
  make run-worker
  ```

  **Terminal 2 (Scheduler de Tarefas):**
  ```bash
  make run-scheduler
  ```

- **Parar Aplicação e Workers**:
  ```bash
  make stop
  ```

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

1. **Exponha a porta local via Ngrok (Obrigatório)**:
   Para que o Twilio se comunique com seu localhost, execute em um novo terminal:
   ```bash
   ngrok http 8000
   ```
   Copie a URL gerada (ex: `https://abcd-123.ngrok-free.app`).

2. **Inicie os Serviços**:
   Certifique-se de ter 3 terminais rodando: `make run-worker`, `make run-scheduler` e `make run`.

3. **Configure o Twilio**:
   No Console do Twilio, defina a URL do webhook para:
   `[SUA_URL_NGROK]/api/v1/twilio/webhook`

4. **Teste**:
   Envie uma mensagem para o número do WhatsApp configurado.

### Acesso à Documentação da API

Com a aplicação rodando localmente (após `make run`), você pode acessar a documentação interativa da API:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 📊 Painéis de Observabilidade e Ferramentas

Com a stack de infraestrutura rodando (via Docker Compose), você tem acesso às seguintes ferramentas de monitoramento e administração:

- **Grafana**: [http://localhost:3000](http://localhost:3000) (Dashboards de métricas e performance)
- **PgAdmin**: [http://localhost:5050](http://localhost:5050) (Administração do Banco de Dados)
- **Prometheus**: [http://localhost:9090](http://localhost:9090) (Coleta e consulta de métricas)
- **Zipkin**: [http://localhost:9411](http://localhost:9411) (Tracing distribuído)

## 📚 Documentação Adicional

- 📝 **[Visão Executiva](docs/v5/executive_overview.md)**
  Visão geral executiva, análise de conformidade e status de maturidade do projeto.

- 📐 **[Arquitetura do Sistema](docs/v4/architecture.md)**
  Detalhes sobre padrões de design, fluxo de dados e decisões arquiteturais.

- 🔧 **[Últimas Correções](docs/v4/last_corrections.md)**
  Histórico recente de refatorações (v4.0), correções de segurança e melhorias de performance.

## 📂 Estrutura de Pastas

```
src/
├── core/         # Infraestrutura base (Config, DB, Queue, DI)
├── modules/      # Domínios de Negócio
│   ├── ai/             # Motores de Inteligência e Agentes
│   ├── channels/       # Integração Twilio/WhatsApp (API, Services)
│   ├── conversation/   # Gestão de Estado e Mensagens (API, Services)
│   ├── identity/       # Gestão de Tenants, Usuários e Permissões (API, Services)
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
