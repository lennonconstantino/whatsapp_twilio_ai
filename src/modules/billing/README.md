# Billing Module 💳

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-stable-success)

## 📝 Descrição

O **Billing Module** é um componente central responsável pelo gerenciamento completo do ciclo de vida de faturamento e monetização do sistema. Ele orquestra planos, assinaturas (subscriptions), controle granular de quotas de uso (features) e integrações robustas com gateway de pagamento (Stripe).

Projetado seguindo os princípios da **Clean Architecture**, o módulo garante alto desacoplamento entre regras de negócio, interfaces de API e persistência de dados, permitindo fácil manutenção, testes isolados e escalabilidade.

## 📸 Preview

*(Placeholder para diagrama de arquitetura ou screenshot do dashboard de billing)*

## ✨ Funcionalidades Principais

- **Gestão de Planos**: Criação e configuração de planos (Free, Pro, Enterprise) com limites personalizados e versionamento.
- **Ciclo de Vida de Assinaturas**: Gestão completa de subscriptions (criação, renovação, cancelamento, upgrade/downgrade).
- **Controle de Quotas (Metering)**: Rastreamento granular de uso de recursos (ex: mensagens enviadas, minutos de IA) com validação em tempo real.
- **Integração Stripe Robusta**:
  - Webhooks para processamento assíncrono e resiliente de eventos de pagamento.
  - Sincronização bidirecional de status de assinatura.
- **Arquitetura Agnóstica**: Repositórios implementados para **Supabase** e **PostgreSQL** nativo, seguindo o padrão Repository.

## 🛠️ Tecnologias Utilizadas

- **Linguagem**: [Python 3.12+](https://www.python.org/)
- **Framework Web**: [FastAPI](https://fastapi.tiangolo.com/)
- **Validação de Dados**: [Pydantic](https://docs.pydantic.dev/)
- **Pagamentos**: [Stripe SDK](https://stripe.com/docs/api)
- **Banco de Dados**: PostgreSQL / Supabase
- **Observabilidade**: OpenTelemetry (Tracing & Metrics)
- **Injeção de Dependência**: Containers customizados para gestão de ciclo de vida de objetos.

## 🏗️ Arquitetura e Diagramas

### Diagrama de Solução (Componentes)

A arquitetura separa claramente as camadas de responsabilidade, isolando o domínio de detalhes de infraestrutura.

```mermaid
graph TD
    subgraph API [API Layer]
        Router[Router API v1]
    end

    subgraph Services [Service Layer]
        SubService[Subscription Service]
        PlanService[Plan Service]
        UsageService[Feature Usage Service]
        WebhookService[Webhook Handler]
    end

    subgraph Infra [Infrastructure Layer]
        StripeClient[Stripe Integration]
        Repo[Repositories Postgres/Supabase]
    end

    subgraph External [External Systems]
        StripeAPI[Stripe API]
        DB[(Database)]
    end

    Router --> SubService
    Router --> PlanService
    
    SubService --> StripeClient
    SubService --> Repo
    WebhookService --> SubService
    
    StripeClient --> StripeAPI
    Repo --> DB
```

### Fluxo de Assinatura (Sequence Diagram)

Fluxo simplificado desde a intenção de compra até a ativação da assinatura via Webhook.

```mermaid
sequenceDiagram
    participant User
    participant API
    participant BillingService
    participant Stripe
    participant WebhookHandler

    User->>API: POST /subscriptions (plan_id)
    API->>BillingService: create_checkout_session(plan_id)
    BillingService->>Stripe: Create Session
    Stripe-->>BillingService: session_url
    BillingService-->>API: payment_link
    API-->>User: Redirect to Stripe

    User->>Stripe: Realiza Pagamento
    Stripe->>WebhookHandler: Event: checkout.session.completed
    WebhookHandler->>BillingService: process_payment_success()
    BillingService->>BillingService: update_subscription_status(ACTIVE)
    BillingService-->>User: Email de Confirmação (Async)
```

### Modelo de Dados (ERD)

Estrutura relacional para gestão de planos, features e assinaturas.

```mermaid
erDiagram
    PLAN ||--|{ PLAN_VERSION : has
    PLAN_VERSION ||--|{ PLAN_FEATURE : contains
    PLAN_VERSION ||--|{ SUBSCRIPTION : defines
    USER ||--|{ SUBSCRIPTION : owns
    SUBSCRIPTION ||--|{ FEATURE_USAGE : tracks
    FEATURE ||--|{ PLAN_FEATURE : included_in
    FEATURE ||--|{ FEATURE_USAGE : usage_of

    PLAN {
        uuid id
        string name
        string slug
    }
    PLAN_VERSION {
        uuid id
        uuid plan_id
        decimal price
        bool active
    }
    SUBSCRIPTION {
        uuid id
        uuid user_id
        uuid plan_version_id
        string stripe_id
        enum status
    }
    FEATURE {
        uuid id
        string code
        enum type
    }
    FEATURE_USAGE {
        uuid id
        uuid subscription_id
        uuid feature_id
        int used_amount
        int quota_limit
    }
```

## 📋 Pré-requisitos

Antes de começar, certifique-se de ter:

- **Python 3.12** ou superior instalado.
- Conta no [Stripe](https://stripe.com/) (com chaves de API de teste/produção).
- Instância **PostgreSQL** ou projeto no [Supabase](https://supabase.com/).
- Variáveis de ambiente configuradas corretamente.

## 🚀 Instalação

1. **Clone o repositório:**
   ```bash
   git clone <url-do-repositorio>
   cd whatsapp_twilio_ai
   ```

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure as Variáveis de Ambiente:**
   Crie um arquivo `.env` baseado no `.env.example` e adicione as credenciais:
   ```env
   # Database
   DATABASE_URL=postgresql://user:pass@localhost:5432/db

   # Stripe
   STRIPE_API_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

## 💻 Uso

### Exemplos de Endpoints

**Listar Planos Disponíveis:**
```http
GET /api/v1/billing/plans
```

**Criar Sessão de Checkout:**
```http
POST /api/v1/billing/subscriptions/checkout
Content-Type: application/json

{
  "plan_id": "plan_pro_monthly"
}
```

**Consultar Uso de Recursos:**
```http
GET /api/v1/billing/usage
```

## 📂 Estrutura de Pastas

```
src/modules/billing/
├── api/                  # Endpoints REST (v1)
├── docs/                 # Documentação técnica e conformidade
├── enums/                # Enumerações (Status, Period, FeatureType)
├── models/               # Modelos de Domínio e Schemas Pydantic
├── repositories/         # Camada de Acesso a Dados (Pattern Repository)
│   ├── impl/             # Implementações Concretas (Postgres, Supabase)
│   └── interfaces.py     # Contratos (ABCs)
├── services/             # Regras de Negócio e Integrações (Stripe)
└── README.md             # Documentação do Módulo
```

## 🤝 Contribuição

Contribuições são bem-vindas! Siga os passos abaixo:

1. Faça um fork do projeto.
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`).
3. Commit suas mudanças (`git commit -m 'Add: nova funcionalidade'`).
4. Push para a branch (`git push origin feature/nova-feature`).
5. Abra um Pull Request.

## 📄 Licença

Este projeto está licenciado sob a licença **MIT** - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Contato

**Equipe de Engenharia**

- **Lead Engineer & Autor**: Lennon
- **Email**: lennonconstantino@gmail.com
- **Time**: Engenharia de IA & Plataforma
