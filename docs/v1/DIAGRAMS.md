# Diagramas da Arquitetura - Owner Project

Este documento contém todos os diagramas Mermaid do projeto. Você pode visualizá-los em:
- GitHub (renderiza Mermaid automaticamente)
- [Mermaid Live Editor](https://mermaid.live)
- VSCode com extensão Mermaid
- Qualquer ferramenta que suporte Mermaid

## 📋 Lista de Diagramas

### 1. Diagrama de Arquitetura Completa
**Arquivo:** `architecture-diagram.mermaid`

Mostra a arquitetura completa do sistema em camadas:
- **External Services**: Twilio API e Client Applications
- **API Layer**: FastAPI endpoints (conversations, webhooks, health)
- **Service Layer**: Business logic (ConversationService, ClosureDetector, TwilioService, AIResultService)
- **Repository Layer**: Data access (7 repositories + base)
- **Database Layer**: Supabase PostgreSQL (7 tables)
- **Models & DTOs**: Domain models, enums, and DTOs

**Cores:**
- 🟢 Verde: API Layer
- 🔵 Azul: Service Layer
- 🟠 Laranja: Repository Layer
- 🟣 Roxo: Database Layer
- ⚫ Cinza: Models/DTOs
- 🔴 Vermelho: External Services

---

### 2. Diagrama de Fluxo de Dados
**Arquivo:** `data-flow-diagram.mermaid`

Diagrama de sequência mostrando 3 fluxos principais:

#### Fluxo 1: Inbound Message (Mensagem Recebida)
```
User → Twilio → Webhook → ConversationService → ClosureDetector → Database
```
Etapas:
1. Usuário envia mensagem via WhatsApp
2. Twilio envia webhook
3. Sistema cria/busca conversa
4. Persiste mensagem
5. ClosureDetector analisa intenção
6. Atualiza status se necessário

#### Fluxo 2: Outbound Message (Mensagem Enviada)
```
API Client → ConversationService → TwilioService → Twilio → User
```
Etapas:
1. Cliente chama API
2. Sistema persiste mensagem
3. TwilioService envia via API
4. Twilio entrega ao usuário

#### Fluxo 3: Timeout Processing (Processamento Automático)
```
Scheduler → ConversationService → Repository → Database
```
Processos:
1. `process_expired_conversations()` - Fecha conversas expiradas
2. `process_idle_conversations()` - Fecha conversas ociosas

---

### 3. Diagrama de Entidades e Relacionamentos (ER)
**Arquivo:** `entity-relationship-diagram.mermaid`

Mostra todas as 7 tabelas e seus relacionamentos:

**Estrutura:**
```
owners (1) → (N) users
owners (1) → (N) features
owners (1) → (1) twilio_accounts
owners (1) → (N) conversations
conversations (1) → (N) messages
messages (1) → (N) ai_results
features (1) → (N) ai_results
```

**Tabelas com todos os campos:**
- ✅ owners (5 campos)
- ✅ users (8 campos)
- ✅ features (7 campos)
- ✅ twilio_accounts (5 campos)
- ✅ conversations (13 campos)
- ✅ messages (12 campos)
- ✅ ai_results (5 campos)

---

### 4. Diagrama de Ciclo de Vida das Conversas
**Arquivo:** `conversation-lifecycle-diagram.mermaid`

State diagram mostrando os estados da conversa:

**Estados Iniciais:**
- `[*]` → `PENDING` (nova conversa)

**Estados Ativos:**
- `PENDING` - Aguardando primeira interação
- `PROGRESS` - Conversa ativa com mensagens

**Estados Finais (Closed):**
- `AGENT_CLOSED` - Fechada por agente
- `SUPPORT_CLOSED` - Fechada por suporte
- `USER_CLOSED` - Fechada por usuário (ClosureDetector)
- `EXPIRED` - Tempo de expiração atingido
- `IDLE_TIMEOUT` - Timeout por inatividade
- `FAILED` - Erro sistêmico

**Transições:**
```
PENDING → PROGRESS (primeira mensagem)
PROGRESS → USER_CLOSED (detecção de encerramento)
PROGRESS → EXPIRED (expires_at < NOW)
PROGRESS → IDLE_TIMEOUT (updated_at timeout)
```

**Notas incluem:**
- Detalhes de cada estado
- Processo de closure detection
- Timeouts automáticos
- Configurações padrão

---

### 5. Diagrama do Algoritmo de Detecção de Encerramento
**Arquivo:** `closure-detection-diagram.mermaid`

Flowchart detalhado do algoritmo ClosureDetector:

**Entrada:** Nova mensagem do usuário

**Verificações:**
1. **Sinal Explícito** (metadata)
   - Se sim → confidence = 1.0, fecha imediatamente

2. **Análise Multi-fatorial:**
   - **Keywords** (peso 0.5):
     - Detecta: tchau, obrigado, valeu, etc.
     - Conta matches
     - Verifica posição (início/fim +bonus)
     - Considera tamanho da mensagem
   
   - **Patterns** (peso 0.3):
     - Resposta curta após IA?
     - Palavras positivas? (sim, ok, certo)
     - Mensagem final após sequência?
   
   - **Context** (peso 0.2):
     - Objetivo alcançado?
     - Sem ações pendentes?
     - Flag can_close ativo?

3. **Duration Check:**
   - Se não passou tempo mínimo → penalidade 50%

**Cálculo Final:**
```
confidence = (keyword * 0.5) + (pattern * 0.3) + (context * 0.2)
```

**Decisão por Threshold:**
- `>= 0.8` 🔴 High: Auto-fecha conversa
- `0.6 - 0.8` 🟠 Medium: Marca no contexto, aguarda
- `< 0.6` 🟢 Low: Continua normal

**Cores no diagrama:**
- 🟢 Verde: Continue/Low confidence
- 🟠 Laranja: Medium confidence
- 🔴 Vermelho: High confidence/Auto-close

---

## 🎨 Como Visualizar

### Opção 1: GitHub
Faça commit dos arquivos `.mermaid` e o GitHub renderizará automaticamente.

### Opção 2: Mermaid Live Editor
1. Acesse https://mermaid.live
2. Copie o conteúdo de qualquer arquivo `.mermaid`
3. Cole no editor
4. Visualize e exporte (PNG, SVG, etc.)

### Opção 3: VSCode
1. Instale a extensão "Markdown Preview Mermaid Support"
2. Abra qualquer arquivo `.mermaid` ou este README
3. Use Preview (Ctrl+Shift+V)

### Opção 4: Markdown com Mermaid
Crie um arquivo markdown e inclua:

```markdown
# Meu Diagrama

```mermaid
[cole o conteúdo do arquivo .mermaid aqui]
```
```

---

## 📊 Resumo dos Diagramas

| Diagrama | Tipo | Foco | Arquivo |
|----------|------|------|---------|
| Arquitetura | Graph | Visão geral do sistema | `architecture-diagram.mermaid` |
| Fluxo de Dados | Sequence | Interações entre componentes | `data-flow-diagram.mermaid` |
| ER | Entity Relationship | Estrutura do banco de dados | `entity-relationship-diagram.mermaid` |
| Ciclo de Vida | State | Estados das conversas | `conversation-lifecycle-diagram.mermaid` |
| Closure Detection | Flowchart | Algoritmo de detecção | `closure-detection-diagram.mermaid` |

---

## 🎯 Uso Recomendado

**Para Desenvolvedores:**
- Use o diagrama de Arquitetura para entender a estrutura
- Consulte o Fluxo de Dados para implementar features
- Revise o ER para queries de banco

**Para Documentação:**
- Inclua os diagramas no README principal
- Use em apresentações e wikis
- Exporte como imagens para relatórios

**Para Novos Membros da Equipe:**
- Comece pelo diagrama de Arquitetura
- Depois veja o Fluxo de Dados
- Estude o Closure Detection para entender a lógica

---

## 🔄 Manutenção

Quando houver mudanças no projeto:
1. Atualize o diagrama correspondente
2. Mantenha consistência com o código
3. Adicione notas explicativas se necessário
4. Exporte novas versões das imagens

---

## 📝 Notas Técnicas

**Versão Mermaid:** Compatível com Mermaid v9+

**Sintaxe:**
- `graph TB` = Top to Bottom
- `sequenceDiagram` = Sequence interactions
- `erDiagram` = Entity Relationship
- `stateDiagram-v2` = State machine

**Limitações:**
- Mermaid não suporta customização avançada de estilos
- Alguns editores podem ter limitações de renderização
- Para diagramas muito complexos, considere ferramentas como draw.io

---

## 🎉 Conclusão

Estes diagramas fornecem uma visão completa e profissional do Owner Project, facilitando:
- ✅ Onboarding de novos desenvolvedores
- ✅ Documentação técnica
- ✅ Apresentações para stakeholders
- ✅ Análise e otimização da arquitetura
- ✅ Manutenção e evolução do sistema
