# 5 Pontos Críticos de Race Conditions Identificados:

1. Background Worker vs Mensagens de Usuário (CRÍTICO)
Arquivos: background_tasks.py, conversation_service.py, webhooks.py
Problema:

Worker detecta conversa idle e começa a fechar
Usuário envia mensagem no meio do processo
Worker sobrescreve a reativação → mensagem perdida

2. Background Worker vs Fechamento Manual (CRÍTICO)
Arquivos: background_tasks.py, conversations.py
Problema:

Agente fecha como AGENT_CLOSED
Worker fecha como EXPIRED simultaneamente
Status final incorreto → métricas erradas

3. Detecção de Closure vs Worker (MODERADO)
Problema:

Sistema detecta "tchau" (80% confiança)
Worker expira antes do fechamento
Conversa fechada como EXPIRED em vez de USER_CLOSED

4. Múltiplas Mensagens Simultâneas (MODERADO)
Problema:

Duas mensagens em <100ms
Ambas leem PENDING
Context "accepted_by" pode ser sobrescrito

5. Cleanup Simultâneos (BAIXO)
Problema: Operação duplicada (mas idempotente)

---

# Exemplos
```plain text
T0: Background Worker lê conversa em PROGRESS (idle há 16 minutos)
T1: Usuário envia mensagem (vai mudar status para PROGRESS e updated_at)
T2: Background Worker fecha conversa como IDLE_TIMEOUT
T3: Sistema recebe mensagem do usuário, mas conversa já está fechada
```

# Cenários Reais de Problemas

## Cenário A: Mensagem Perdida
```plain text
Timeline:
09:00:00 - Conversa em PROGRESS, updated_at=08:45:00
09:00:01 - Background Worker: Query retorna conversa (idle 15min)
09:00:02 - Usuário envia: "Obrigado!"
09:00:03 - Webhook: Atualiza updated_at=09:00:03, status=PROGRESS
09:00:04 - Background Worker: Fecha como IDLE_TIMEOUT
09:00:05 - Usuário envia: "Posso fazer outra pergunta?"
09:00:06 - Webhook: Conversa está fechada → Cria nova conversa
```
Problema:

Primeira mensagem "Obrigado!" foi perdida
Nova conversa criada sem contexto
Usuário confuso

## Cenário B: Status Incorreto
```plain text
Timeline:
10:00:00 - Conversa em PROGRESS
10:00:01 - Usuário: "Ok, pode fechar então"
10:00:02 - Sistema detecta closure (85% confiança)
10:00:03 - Background Worker: Query retorna conversa expirada
10:00:04 - Sistema: Tentando fechar como USER_CLOSED
10:00:05 - Background Worker: Fecha como EXPIRED (ganhou a corrida)
```
Problema:

Métricas mostram EXPIRED (não USER_CLOSED)
Analytics incorretos: parece abandono (não encerramento voluntário)
SLA de resposta incorreto

## Cenário C: Fechamento Duplo
```plain text
Timeline:
11:00:00 - Conversa em PROGRESS
11:00:01 - Agente clica "Encerrar" → API POST /close
11:00:02 - API: Lê conversa, valida, prepara para fechar
11:00:03 - Background Worker: Detecta expiração, fecha como EXPIRED
11:00:04 - API: Tenta fechar como AGENT_CLOSED
11:00:05 - Validação: EXPIRED → AGENT_CLOSED é inválida (warning)
11:00:06 - Conversa permanece como EXPIRED
```
Problema:

Agente acha que fechou, mas status é EXPIRED
Relatórios de performance do agente incorretos
Gamificação/bonificação afetada