# Conversation Module Refactoring

Code Smells (Arquivos Críticos)
Identifiquei violações da regra de limite de linhas (300 linhas) que indicam acúmulo de responsabilidades (God Class/God Object):

1. 🔴 conversation_service.py (1108 linhas)
    - Diagnóstico : É o maior gargalo de manutenção do sistema. Mistura responsabilidades de:
        - Busca/Criação de conversas ( get_or_create ).
        - Gerenciamento de ciclo de vida (expiração, timeouts).
        - Lógica de negócio de mensagens.
        - Detecção de intenção de encerramento.
    - Impacto : Alta complexidade ciclomática, difícil de testar e alto risco de regressão em alterações.
2. 🟠 conversation_repository.py (853 linhas)
    - Diagnóstico : Provavelmente contém regras de negócio vazadas para a camada de dados (queries muito complexas ou filtragens que deveriam estar no Service).
