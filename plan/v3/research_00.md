Para implementar um rastreamento robusto (tracing) que conecte a Causa (Mensagem do Usuário), o Processamento (IA) e o Efeito (Resposta do Sistema), o correlation_id deve atuar como o elo de ligação de uma "transação lógica" única.

Analisando a arquitetura atual ( 001_initial_schema.sql e webhooks.py ), esta é a estrutura recomendada:

### 1. Onde colocar o campo?
Você deve adicionar o campo correlation_id em duas tabelas principais:

1. messages : Para agrupar a mensagem de entrada (User) e a mensagem de saída (Agent/System) sob o mesmo identificador de transação.
2. ai_results : Para vincular o "pensamento" e os metadados da IA (tokens, confidence, intenção) diretamente a essa transação, sem depender apenas do msg_id .
### 2. Por que nessas tabelas?
- Na messages : Atualmente, as mensagens são ligadas apenas pela conv_id (sessão longa). O correlation_id permite que você diga: "Esta mensagem de resposta (Outbound) é filha direta desta mensagem de entrada (Inbound)" .
- Na ai_results : Embora ai_results já tenha msg_id (da mensagem de entrada), ter o correlation_id indexado permite consultas de "visão geral" muito mais rápidas (ex: "Me dê todos os logs, mensagens e resultados da transação X") sem joins complexos.
### 3. Tabelas a Atualizar (Plano de Migração)
Aqui está o SQL sugerido para atualizar seu esquema. Recomendo criar um arquivo de migração (ex: migrations/002_add_correlation_id.sql ):

```
-- 1. Adicionar correlation_id na tabela messages
ALTER TABLE messages 
ADD COLUMN correlation_id TEXT;

-- Indexar para buscas rápidas de histórico de uma transação
CREATE INDEX idx_messages_correlation_id ON messages
(correlation_id);

-- 2. Adicionar correlation_id na tabela ai_results
ALTER TABLE ai_results 
ADD COLUMN correlation_id TEXT;

-- Indexar para cruzar com mensagens rapidamente
CREATE INDEX idx_ai_results_correlation_id ON ai_results
(correlation_id);

-- Comentários para documentação
COMMENT ON COLUMN messages.correlation_id IS 'Trace ID linking 
inbound trigger to outbound response';
COMMENT ON COLUMN ai_results.correlation_id IS 'Trace ID linking 
AI processing to the specific interaction cycle';
```
### 4. Impacto no Código (webhooks.py)
No seu arquivo src/modules/channels/twilio/api/webhooks.py , a lógica já prepara o terreno, mas precisa persistir esse dado.

Fluxo Ideal:

1. Inbound: Recebe webhook → Gera correlation_id (usando MessageSid do Twilio ou UUID) → Salva na messages (inbound).
2. Process: Passa correlation_id para o Agente → Agente processa → Salva ai_results com esse correlation_id .
3. Outbound: Agente retorna resposta → Salva na messages (outbound) usando o mesmo correlation_id da entrada (e não um novo).
