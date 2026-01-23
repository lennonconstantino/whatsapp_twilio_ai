# Diagramas do Sistema

Este documento lista e descreve os diagramas técnicos gerados para documentar visualmente a arquitetura e fluxos do sistema. Os arquivos fonte `.mermaid` encontram-se no mesmo diretório.

## 1. Diagrama de Arquitetura (`architecture-diagrama.mermaid`)
Representa a visão de alto nível dos componentes do sistema, incluindo:
- **API Gateway**: Pontos de entrada REST.
- **Core Services**: Injeção de dependência, Filas, Configuração.
- **Módulos**: Twilio, Conversation, AI, Identity.
- **Infraestrutura Externa**: Supabase (DB), Twilio (Messaging), OpenAI (LLM).

## 2. Diagrama de Ciclo de Vida da Conversa (`conversation-lifecycle-diagram.mermeid`)
Ilustra a Máquina de Estados Finita (FSM) que governa as conversas.
- Detalha os estados (`PENDING`, `PROGRESS`, `IDLE`, `CLOSED`...) e as transições permitidas.
- Mostra os gatilhos de transição (ex: timeout, ação do usuário, comando do agente).

## 3. Diagrama de Fluxo de Dados (`data-flow-diagram.mermeid`)
Mapeia a jornada de uma mensagem desde o recebimento até a resposta.
- Webhook Ingress -> Fila de Processamento -> Motor de IA -> Resposta Outbound.
- Destaca os pontos de persistência e decisão assíncrona.

## 4. Diagrama de Entidade-Relacionamento (`entity-relationship-diagram.mermeid`)
Esquema do banco de dados relacional.
- Tabelas principais: `owners`, `users`, `conversations`, `messages`, `twilio_accounts`.
- Relacionamentos e chaves estrangeiras.

## 5. Diagrama de Detecção de Encerramento (`closure-detection-diagram.mermaid`)
Fluxograma detalhado do processo de background que monitora conversas.
- Lógica de verificação de inatividade (Idle Timeout).
- Lógica de expiração total (TTL).
- Interação entre o Scheduler e o QueueService.
