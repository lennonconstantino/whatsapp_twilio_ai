# Structure v1 - v3.1.0

```text plain
src/
├── core/                   # O "Kernel" do sistema (infraestrutura pura)
│   ├── config/             # settings.py
│   ├── database/           # conexão, base repositories
│   ├── utils/              # logging, helpers genéricos
│   └── errors/             # exceções globais
│
├── modules/                # Onde a mágica acontece (Domínios)
│   │
│   ├── conversation/       # DOMÍNIO 1: Gestão do estado e fluxo
│   │   ├── api/            # rotas (ex: conversations.py)
│   │   ├── services/       # ConversationService
│   │   ├── repositories/   # ConversationRepo, MessageRepo
│   │   ├── models/         # Entidades (Conversation, Message)
│   │   └── workers/        # Tarefas de timeout/expiração
│   │
│   ├── intelligence/       # DOMÍNIO 2: O "Cérebro" (IA)
│   │   ├── services/       # ClosureDetector, AIResultService
│   │   ├── repositories/   # AIResultRepository
│   │   └── prompts/        # Templates de prompt (se houver)
│   │
│   ├── channels/           # DOMÍNIO 3: Integrações Externas (Twilio)
│   │   ├── whatsapp/       # Sub-domínio específico
│   │   │   ├── api/        # webhooks.py
│   │   │   ├── services/   # TwilioService
│   │   │   └── workers/    # Sender worker
│   │   └── repositories/   # TwilioAccountRepository
│   │
│   └── identity/           # DOMÍNIO 4: Usuários e Donos
│       ├── repositories/   # OwnerRepository, UserRepository
│       └── models/
│
└── main.py                 # "Composition Root" (junta tudo e inicia)
```