# Decisão sobre o módulo `src/modules/ai/ai_result/`

**Veredito:** **MANTER O MÓDULO.**

## Racional

Após analisar o código fonte de `AILogThoughtService` e `AIResultRepository`, constatei que este módulo serve a um propósito **distinto** e **complementar** ao módulo de conversação.

### Diferenciação Clara

1.  **Módulo `conversation` (O "O Quê"):**
    *   Armazena a **interação final** entre usuário e sistema.
    *   Exemplo: Usuário diz "Saldo?", Sistema responde "R$ 100".
    *   É a fonte de verdade para o **Histórico de Chat** e para o contexto (RAG) da IA.

2.  **Módulo `ai_result` (O "Como"):**
    *   Armazena o **processo de pensamento** e **metadados de execução** da IA.
    *   Exemplo:
        *   "Agente decidiu chamar a tool `get_finance_balance`".
        *   "Tool retornou JSON `{amount: 100}`".
        *   "Custo da operação: 150 tokens".
        *   "Trace ID: xyz-123".
    *   Funciona como um **Log de Auditoria e Observabilidade**.

### Por que manter?

*   **Debugging:** Se o agente der uma resposta errada, você precisa saber *por que* (qual tool falhou? qual foi o raciocínio?). Essa informação está no `ai_result`, não na mensagem do chat.
*   **Analytics:** Permite analisar quais ferramentas são mais usadas, latência de cada passo e custos de token.
*   **Auditoria:** Em cenários financeiros (como o módulo `finance`), é crucial ter o registro de que a IA executou uma ação baseada em um dado retorno de ferramenta.

### Conclusão

Não há duplicação funcional. O `ai_result` enriquece o sistema com "metacognição" da IA, enquanto o `conversation` cuida da "comunicação". Ambos devem coexistir.

A estratégia de memória (RAG) consumirá o `conversation`, enquanto a estratégia de monitoramento consumirá o `ai_result`.
