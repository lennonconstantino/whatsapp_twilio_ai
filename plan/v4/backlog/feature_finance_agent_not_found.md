O log que você identificou ( Feature 'finance_agent' not found, defaulting to 'finance' ) indica um pequeno desalinhamento de configuração, mas não é um erro crítico . O sistema está funcionando graças a um mecanismo de fallback (segurança).

### O que está acontecendo?
1. No Banco de Dados : A funcionalidade está cadastrada com o nome finance_agent (conforme definido no script de seed).
2. No Código (AgentFactory) : A fábrica de agentes estava configurada para reconhecer apenas a chave finance .
3. O Log : Quando o sistema tenta carregar o agente para finance_agent , a fábrica não encontra o registro exato, emite esse aviso (INFO) e usa o agente de finance como padrão.
### A Correção Aplicada
Para eliminar esse aviso e tornar a configuração explícita, ajustei o arquivo de injeção de dependências ( container.py ) para reconhecer ambos os nomes.

Arquivo Alterado: src/core/di/container.py

```
agents_registry=providers.Dict(
    finance=finance_agent.provider,
    finance_agent=finance_agent.provider, # 
    Alias adicionado
    relationships=relationships_agent.provider,
),
```
Agora o sistema mapeia corretamente finance_agent para o agente de finanças sem precisar acionar o mecanismo de fallback ou gerar logs de aviso.

```
{"event": "Feature 'finance_agent' not found, defaulting to 'finance'", "logger": "src.modules.ai.engines.lchain.core.agents.agent_factory", "level": "info", "timestamp": "2026-01-28T02:21:54.823216Z"}
```
