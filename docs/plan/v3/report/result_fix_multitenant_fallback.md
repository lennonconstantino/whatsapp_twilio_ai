# Relatório de Correção: Fallback de Multi-Tenant Perigoso

## Contexto
Conforme identificado na análise técnica (`research_04.md`, item 5), o sistema possuía um mecanismo de fallback que utilizava as credenciais padrão do Twilio (definidas no `.env`) quando não encontrava uma conta específica para o número de telefone ou `owner_id`.

## Problema
Em um ambiente SaaS Multi-Tenant (Produção), esse comportamento apresenta riscos críticos:
1.  **Mistura de Dados:** Mensagens destinadas a um tenant não configurado poderiam ser processadas pela conta "default" (geralmente a do admin ou da plataforma), misturando conversas de clientes diferentes.
2.  **Cobrança Indevida:** O envio de mensagens usando a conta default para tenants órfãos geraria custos para a plataforma, em vez de falhar ou cobrar o cliente correto.
3.  **Inconsistência:** O sistema poderia mascarar erros de configuração de novos tenants, dificultando o diagnóstico.

## Solução Aplicada
O mecanismo de fallback foi restrito estritamente ao ambiente de desenvolvimento (`development`). Em produção, se a conta não for encontrada, o sistema agora falhará de forma segura (retornando erro ou `None`), garantindo que nenhuma mensagem seja processada no contexto errado.

### Alterações Realizadas

#### 1. Resolução de Conta (`TwilioAccountService`)
Arquivo: `src/modules/channels/twilio/services/twilio_account_service.py`

O fallback para `settings.twilio.account_sid` agora é condicionado a `settings.api.environment == "development"`.

```python
# Antes
if not account and getattr(settings.twilio, "account_sid", None):
     account = self.repo.find_by_account_sid(settings.twilio.account_sid)

# Depois
if getattr(settings.api, "environment", "production") == "development":
    if not account and getattr(settings.twilio, "account_sid", None):
         account = self.repo.find_by_account_sid(settings.twilio.account_sid)
```

#### 2. Envio de Mensagens (`TwilioService`)
Arquivo: `src/modules/channels/twilio/services/twilio_service.py`

O uso de credenciais padrão para envio também foi restrito.

```python
# Antes
if settings.twilio.account_sid and settings.twilio.auth_token:
    logger.info("Using default Twilio credentials")
    # ...

# Depois
if settings.api.environment == "development" and settings.twilio.account_sid and settings.twilio.auth_token:
    logger.info("Using default Twilio credentials (Development Mode)")
    # ...
```

## Impacto
- **Produção:** Mais segura e estrita. Erros de configuração de tenant resultarão em falhas visíveis (logs de erro) em vez de processamento incorreto silencioso.
- **Desenvolvimento:** Mantida a facilidade de uso com credenciais globais no `.env` para testes rápidos sem necessidade de popular o banco de dados de tenants.

## Próximos Passos
- Monitorar logs de produção por `Owner lookup failed` ou `No Twilio account found for owner` para identificar tenants mal configurados.
