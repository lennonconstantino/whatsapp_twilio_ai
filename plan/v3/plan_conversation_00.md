# Tenho um plano de refatoração em mente:

** Manter o mesmo funcionamento do ConversationService original, garantindo que as interações com o usuário permaneçam a mesma.**

1. Refatoração Estrutural (Médio/Longo) :
    - Dividir ConversationService em serviços menores: 
        - ConversationFinder - Responsável por buscar ou criar conversas.
        - ConversationLifecycle - Gerenciar o ciclo de vida da conversa (expiração, timeouts).
        - ConversationCloser - Detectar e encerrar conversas baseadas na intenção do usuário.
    - Remover a instanciação manual nos construtores (forçar injeção via Container).
2. Isolar Lógica de Busca : Criar ConversationFinder para remover o get_or_create do Service principal.
3. Isolar Ciclo de Vida : Criar ConversationLifecycle para lidar com timeouts e expiração.
Isso reduziria drasticamente o tamanho da classe principal e facilitaria os testes.
4. criar Testes Unitários para os Novos Serviços :
    - Testar cada serviço separadamente, garantindo que cada uma tenha a responsabilidade correta.
    - Utilizar mocks para simular interações com o repositório e outros serviços.