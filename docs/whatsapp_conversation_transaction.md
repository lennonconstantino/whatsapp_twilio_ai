# Transações e Interações - Ciclo de Vida de Conversas WhatsApp

## Estados do Sistema

### Estados Ativos
- **PENDING**: Conversa ativa, aguardando interação
- **PROGRESS**: Conversa em andamento
- **IDLE_TIMEOUT**: Conversa pausada por inatividade

### Estados Finais
- **AGENT_CLOSED**: Conversa encerrada pelo agente
- **SUPPORT_CLOSED**: Conversa encerrada pela equipe de suporte
- **USER_CLOSED**: Conversa encerrada pelo usuário
- **EXPIRED**: Conversa expirada automaticamente pelo sistema
- **FAILED**: Conversa encerrada por falha no sistema

---

## Matriz de Transições de Estado

### 1. PENDING → Outros Estados

| Transição | Evento/Gatilho | Descrição |
|-----------|---------------|-----------|
| PENDING → PROGRESS | Agente aceita conversa / Primeira resposta do agente | Agente inicia atendimento da conversa pendente |
| PENDING → EXPIRED | Timer de espera excedido (ex: 24-48h sem atendimento) | Sistema expira conversa não atendida |
| PENDING → SUPPORT_CLOSED | Suporte cancela conversa na fila | Equipe de suporte decide encerrar sem atendimento |
| PENDING → USER_CLOSED | Usuário cancela solicitação / Envia comando de cancelamento | Usuário desiste antes do atendimento |
| PENDING → FAILED | Erro crítico do sistema / Falha na infraestrutura | Sistema não consegue processar a conversa |

### 2. PROGRESS → Outros Estados

| Transição | Evento/Gatilho | Descrição |
|-----------|---------------|-----------|
| PROGRESS → AGENT_CLOSED | Agente clica em "Encerrar conversa" / Resolve o atendimento | Agente finaliza atendimento com sucesso |
| PROGRESS → SUPPORT_CLOSED | Supervisor/Admin encerra conversa / Escalação resolvida | Equipe de suporte intervém e finaliza |
| PROGRESS → USER_CLOSED | Usuário envia "Sair" / "Cancelar" / Encerra conversa | Usuário decide encerrar atendimento |
| PROGRESS → IDLE_TIMEOUT | Inatividade de X minutos (ex: 10-15 min) sem mensagens | Sistema pausa conversa por inatividade |
| PROGRESS → EXPIRED | Timer máximo de conversa excedido (ex: 24h) | Sistema encerra por tempo limite |
| PROGRESS → FAILED | Erro de conexão / Falha na API do WhatsApp / Perda de sessão | Sistema falha durante atendimento |

### 3. IDLE_TIMEOUT → Outros Estados

| Transição | Evento/Gatilho | Descrição |
|-----------|---------------|-----------|
| IDLE_TIMEOUT → PROGRESS | Usuário ou agente envia nova mensagem | Conversa é reativada |
| IDLE_TIMEOUT → EXPIRED | Timer de timeout estendido excedido (ex: 1-2h sem atividade) | Sistema expira conversa pausada |
| IDLE_TIMEOUT → AGENT_CLOSED | Agente decide encerrar durante pausa | Agente finaliza conversa inativa |
| IDLE_TIMEOUT → USER_CLOSED | Usuário envia comando de encerramento | Usuário encerra durante pausa |
| IDLE_TIMEOUT → FAILED | Erro ao tentar reativar / Sessão perdida | Sistema falha ao gerenciar timeout |

### 4. Estados Finais (Sem Transições de Saída)

Os estados **AGENT_CLOSED**, **SUPPORT_CLOSED**, **USER_CLOSED**, **EXPIRED** e **FAILED** são estados terminais. Uma vez que a conversa atinge esses estados, ela não pode transicionar para outros estados. Uma nova conversa seria iniciada do estado PENDING.

---

## Exemplos de Fluxos Comuns

### Fluxo 1: Atendimento Bem-Sucedido
```
PENDING → PROGRESS → AGENT_CLOSED
```
**Descrição**: Usuário abre conversa → Agente atende → Problema resolvido → Agente encerra

### Fluxo 2: Usuário Desiste Durante Atendimento
```
PENDING → PROGRESS → USER_CLOSED
```
**Descrição**: Usuário abre conversa → Agente atende → Usuário decide encerrar

### Fluxo 3: Conversa com Pausa por Inatividade
```
PENDING → PROGRESS → IDLE_TIMEOUT → PROGRESS → AGENT_CLOSED
```
**Descrição**: Usuário abre conversa → Agente atende → Inatividade → Reativação → Resolução

### Fluxo 4: Timeout Completo
```
PENDING → PROGRESS → IDLE_TIMEOUT → EXPIRED
```
**Descrição**: Usuário abre conversa → Agente atende → Inatividade prolongada → Sistema expira

### Fluxo 5: Conversa Não Atendida
```
PENDING → EXPIRED
```
**Descrição**: Usuário abre conversa → Nenhum agente disponível por muito tempo → Sistema expira

### Fluxo 6: Falha Técnica
```
PENDING → PROGRESS → FAILED
```
**Descrição**: Usuário abre conversa → Agente atende → Erro crítico ocorre → Sistema falha

### Fluxo 7: Intervenção de Suporte
```
PENDING → PROGRESS → SUPPORT_CLOSED
```
**Descrição**: Usuário abre conversa → Agente atende → Supervisor intervém e resolve → Suporte encerra

---

## Detalhamento de Interações por Estado

### Estado PENDING

**Ações Permitidas:**
- Visualizar mensagem inicial do usuário
- Aceitar conversa (transição para PROGRESS)
- Transferir para outro agente/departamento
- Cancelar/Rejeitar (transição para SUPPORT_CLOSED)

**Interações do Usuário:**
- Enviar mensagens adicionais (permanecem em PENDING)
- Cancelar solicitação (transição para USER_CLOSED)
- Aguardar atendimento

**Automações:**
- Mensagem automática de confirmação de recebimento
- Notificações de posição na fila
- Timer de expiração em execução

---

### Estado PROGRESS

**Ações do Agente:**
- Enviar mensagens
- Enviar arquivos/mídia
- Usar respostas rápidas/templates
- Transferir conversa para outro agente
- Escalar para supervisor
- Adicionar notas internas
- Encerrar conversa (transição para AGENT_CLOSED)

**Interações do Usuário:**
- Enviar mensagens
- Enviar arquivos/mídia
- Enviar localização
- Solicitar encerramento (transição para USER_CLOSED)

**Automações:**
- Detecção de inatividade (timer para IDLE_TIMEOUT)
- Sincronização de mensagens com WhatsApp
- Logging de todas as interações
- Timer de duração máxima da conversa

---

### Estado IDLE_TIMEOUT

**Ações do Agente:**
- Enviar mensagem para reativar (transição para PROGRESS)
- Encerrar conversa (transição para AGENT_CLOSED)
- Adicionar nota sobre motivo da inatividade

**Interações do Usuário:**
- Enviar mensagem (transição para PROGRESS - reativação automática)
- Encerrar conversa (transição para USER_CLOSED)

**Automações:**
- Mensagem automática: "Notamos que você está inativo. A conversa será encerrada em X minutos."
- Timer estendido de expiração
- Notificação ao agente sobre status de timeout

---

### Estados Finais - Ações Pós-Encerramento

**Disponíveis em todos os estados finais:**
- Visualizar histórico completo da conversa
- Exportar conversa
- Reabrir conversa (cria nova conversa em PENDING)
- Adicionar tags/categorias
- Avaliar atendimento (quando aplicável)

**AGENT_CLOSED:**
- Agente pode adicionar resumo do atendimento
- Registrar solução aplicada
- Marcar como resolvido/não resolvido

**SUPPORT_CLOSED:**
- Documentar motivo da intervenção
- Adicionar feedback para agente
- Registrar ações tomadas

**USER_CLOSED:**
- Registrar motivo do encerramento (se fornecido)
- Opção de pesquisa de satisfação

**EXPIRED:**
- Log automático do motivo (timeout específico)
- Notificação para gestores sobre conversa expirada

**FAILED:**
- Log detalhado de erro
- Alerta técnico para equipe de TI
- Tentativa de recuperação de dados

---

## Regras de Negócio Importantes

### Prioridade de Transições Conflitantes
1. **FAILED** tem prioridade máxima (erros críticos)
2. **USER_CLOSED** tem prioridade sobre ações do agente
3. **SUPPORT_CLOSED** pode sobrescrever AGENT_CLOSED
4. **EXPIRED** só ocorre se nenhuma outra transição acontecer

### Timers Sugeridos
- **PENDING → EXPIRED**: 24-48 horas
- **PROGRESS → IDLE_TIMEOUT**: 10-15 minutos
- **IDLE_TIMEOUT → EXPIRED**: 1-2 horas
- **PROGRESS → EXPIRED**: 24 horas (duração máxima)

### Notificações
- **PENDING**: Notificar agentes disponíveis
- **PROGRESS**: Alertas de inatividade
- **IDLE_TIMEOUT**: Aviso ao usuário e agente
- **Estados Finais**: Confirmação de encerramento

### Métricas Importantes
- Tempo médio em PENDING
- Taxa de conversão PENDING → PROGRESS
- Tempo médio em PROGRESS
- Taxa de IDLE_TIMEOUT
- Taxa de cada tipo de encerramento
- Taxa de FAILED (indicador de saúde do sistema)

---

## Casos Especiais

### Transferência de Agente
```
PROGRESS (Agente A) → PENDING (transferência) → PROGRESS (Agente B)
```
A conversa retorna brevemente a PENDING durante transferência interna.

### Escalação para Supervisor
```
PROGRESS (Agente) → PROGRESS (Supervisor) → SUPPORT_CLOSED
```
Não há mudança de estado, mas há mudança de responsável.

### Reconexão Após Falha
```
FAILED → [Nova conversa] → PENDING
```
Sistema cria nova conversa referenciando a que falhou.

### Retorno Após Expiração
```
EXPIRED → [Nova conversa] → PENDING
```
Usuário retorna, sistema cria nova conversa e pode vincular ao histórico anterior.

---

## Auditoria e Compliance

Todas as transições devem registrar:
- Timestamp da transição
- Estado anterior e novo estado
- Usuário/Sistema que iniciou a transição
- Motivo da transição (quando aplicável)
- Metadados relevantes (ex: tempo total em cada estado)

Essa auditoria permite análise de:
- Eficiência do atendimento
- Identificação de gargalos
- Padrões de comportamento
- Problemas técnicos recorrentes