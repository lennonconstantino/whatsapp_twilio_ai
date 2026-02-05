### 4. Plano de Implementação Sugerido
Caso concorde, minha sugestão de roteiro é:

1. Refatoração do Service : Ajustar AIResultService para aceitar msg_id como string (ULID) e alinhar com o Model.
2. Enriquecimento de Contexto : Adicionar feature_id ao AgentContext para que o agente saiba "quem ele é" no contexto da aplicação.
3. Integração (Via Wrapper) :
   - Não alterar o código interno do Agent.run para chamar o banco (violaria Single Responsibility).
   - Criar um método na camada de aplicação (ou no Infrastructure ) que orquestra: Executa Agente -> Captura Resultado -> Chama AIResultService .