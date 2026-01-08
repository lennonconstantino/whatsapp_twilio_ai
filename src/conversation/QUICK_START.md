# Quick Start - Conversation Manager

## 🚀 Instalação Rápida

### 1. Extrair arquivos
```bash
unzip conversation_manager.zip
cd conversation_manager
```

### 2. Instalar dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar ambiente
```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar com suas credenciais do Supabase
nano .env
```

Configurar no `.env`:
```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon
DATABASE_SCHEMA=conversations
CONVERSATION_EXPIRY_HOURS=24
IDLE_TIMEOUT_MINUTES=30
```

### 4. Setup do banco de dados
```bash
python -m conversation_manager.scripts.setup_database
```

### 5. (Opcional) Carregar dados fake
```bash
python -m conversation_manager.seeds.load_seeds
```

### 6. Testar
```bash
python -m conversation_manager.examples.basic_usage
```

---

## 📋 Checklist de Setup

- [ ] Python 3.10+ instalado
- [ ] Projeto Supabase criado
- [ ] Dependências instaladas
- [ ] Arquivo `.env` configurado
- [ ] Schema do banco criado
- [ ] Dados fake carregados (opcional)
- [ ] Exemplos executados com sucesso

---

## 🎯 Uso Básico em 3 Passos

### 1. Criar uma conversa
```python
from conversation_manager.service.conversation_service import ConversationService

service = ConversationService()
conversation = await service.create_conversation(
    phone_number="+5511999999999",
    channel="whatsapp"
)
```

### 2. Enviar/Receber mensagens
```python
from conversation_manager.service.message_service import MessageService

msg_service = MessageService()

# Receber do usuário
await msg_service.receive_user_message(
    conversation.id,
    content="Olá, preciso de ajuda!"
)

# Enviar resposta
await msg_service.send_agent_message(
    conversation.id,
    content="Olá! Como posso ajudá-lo?"
)
```

### 3. Fechar conversa
```python
# Fechamento automático por palavras-chave
await msg_service.receive_user_message(
    conversation.id,
    content="Obrigado! Tchau."
)
# Conversa será fechada automaticamente!

# Ou fechamento manual
await service.close_conversation(conversation.id, closed_by="agent")
```

---

## 📚 Documentação

- **README.md** - Visão geral do projeto
- **USAGE_GUIDE.md** - Guia completo de uso
- **ARCHITECTURE.md** - Detalhes da arquitetura
- **examples/basic_usage.py** - Exemplos práticos

---

## 🏗️ Estrutura do Projeto

```
conversation_manager/
├── entity/          # Entidades do domínio (Conversation, Message)
├── repository/      # Acesso a dados (Supabase)
├── service/         # Lógica de negócio
├── view/            # DTOs para APIs
├── config/          # Configurações
├── scripts/         # Setup do banco
├── seeds/           # Dados fake
└── examples/        # Exemplos de uso
```

---

## 🔑 Recursos Principais

### ✅ Gestão Completa de Conversas
- Criação e gerenciamento de conversas
- Máquina de estados com transições validadas
- Contexto personalizável por conversa

### ✅ Sistema de Mensagens
- Suporte a texto, imagem, áudio, vídeo, documentos
- Rastreamento de direção (inbound/outbound)
- Categorização por proprietário (user, agent, system, tool, support)

### ✅ Detecção Inteligente de Encerramento
- Análise de palavras-chave configuráveis
- Sinais explícitos via metadados
- Eventos de canal (conversation_end, user_left, etc)

### ✅ Background Jobs
- Expiração automática de conversas antigas
- Detecção de conversas inativas
- Intervalos configuráveis

### ✅ Arquitetura em Camadas
- Entity, Repository, Service, View
- Fácil manutenção e testes
- Extensível para novos recursos

---

## 🔧 Configurações Importantes

### Palavras-chave de Encerramento
Configure em `config/settings.py` ou via variável de ambiente:
```python
CLOSURE_KEYWORDS = [
    "obrigado", "obrigada", "tchau", "até logo",
    "valeu", "pode fechar", "já resolvi"
]
```

### Tempo de Expiração
```env
CONVERSATION_EXPIRY_HOURS=24  # Conversas expiram após 24h
IDLE_TIMEOUT_MINUTES=30       # Inativas após 30min
```

### Intervalos dos Background Jobs
```env
CLEANUP_JOB_INTERVAL_MINUTES=15   # Verifica inativas a cada 15min
EXPIRY_CHECK_INTERVAL_MINUTES=5   # Verifica expiradas a cada 5min
```

---

## 🎨 Exemplos de Integração

### WhatsApp Webhook
```python
async def handle_whatsapp_webhook(data):
    phone = data["from"]
    message = data["text"]
    
    # Buscar ou criar conversa
    conv = await conv_service.get_active_conversation(phone)
    if not conv:
        conv = await conv_service.create_conversation(
            phone_number=phone,
            channel="whatsapp"
        )
    
    # Processar mensagem
    await msg_service.receive_user_message(
        conv.id,
        content=message
    )
    
    # Gerar e enviar resposta
    response = generate_ai_response(message)
    await msg_service.send_agent_message(conv.id, response)
```

### API REST com FastAPI
```python
from fastapi import FastAPI
from conversation_manager.view import *

app = FastAPI()

@app.post("/conversations")
async def create_conversation(dto: ConversationCreateDTO):
    conv = await conv_service.create_conversation(
        dto.phone_number,
        dto.channel,
        dto.initial_context
    )
    return ConversationResponseDTO.from_entity(conv)

@app.post("/messages")
async def send_message(dto: SendMessageDTO):
    msg = await msg_service.send_agent_message(
        dto.conversation_id,
        dto.content
    )
    return MessageResponseDTO.from_entity(msg)
```

---

## 🐛 Troubleshooting

### Erro: "Supabase connection failed"
- Verifique URL e KEY no `.env`
- Confirme que o projeto Supabase está ativo

### Erro: "Table not found"
- Execute o script de setup do banco
- Verifique se o schema `conversations` foi criado

### Conversa não fecha automaticamente
- Verifique se as palavras-chave estão configuradas
- Confirme que a mensagem é do tipo USER
- Veja logs para debug

### Background jobs não funcionam
- Certifique-se de chamar `await start_background_jobs()`
- Mantenha o event loop rodando
- Verifique os intervalos configurados

---

## 📞 Próximos Passos

1. **Personalizar palavras-chave** de encerramento para seu caso de uso
2. **Integrar com seu canal** (WhatsApp, Telegram, WebChat)
3. **Adicionar IA** para gerar respostas automáticas
4. **Implementar webhooks** para notificações
5. **Criar dashboard** para monitoramento

---

## 🤝 Contribuindo

Este módulo foi desenvolvido com foco em extensibilidade. Você pode:

- Adicionar novos tipos de mensagens
- Criar estratégias de detecção de intenção
- Implementar novos canais de comunicação
- Adicionar analytics e métricas

Consulte **ARCHITECTURE.md** para detalhes sobre a estrutura e padrões utilizados.

---

## 📄 Licença

Este código foi desenvolvido como um módulo personalizado para gestão de conversas.

---

## 🎓 Recursos Adicionais

- [Documentação Supabase](https://supabase.com/docs)
- [Guia Python Async/Await](https://docs.python.org/3/library/asyncio.html)
- [Padrões de Design](https://refactoring.guru/design-patterns)

---

**Desenvolvido com ❤️ para facilitar a integração de agentes de IA em conversas**
