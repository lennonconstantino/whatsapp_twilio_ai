# Relatório de Implementação: Suporte a AWS SQS

## Resumo
Este relatório documenta a implementação do suporte ao **AWS SQS** (Simple Queue Service) como backend de fila, oferecendo uma opção robusta e gerenciada para cenários de alto volume de mensagens (Enterprise).

## Mudanças Realizadas

### 1. Novo Backend `SQSBackend`
Criado em `src/core/queue/backends/sqs.py`.
*   Implementa a interface `QueueBackend` utilizando `boto3`.
*   **Enqueue**: Envia mensagens para o SQS serializando o `QueueMessage` em JSON.
*   **Dequeue**: Utiliza *Long Polling* (`WaitTimeSeconds=5`) para reduzir chamadas vazias e custos.
    *   Mapeia o `ReceiptHandle` do SQS para o `id` da mensagem interna para garantir que o `ack` funcione corretamente (já que o SQS exige o handle para deleção).
*   **Ack**: Remove a mensagem do SQS usando o `delete_message`.
*   **Nack**: Altera a visibilidade da mensagem (`change_message_visibility`) para reaparecer na fila após um atraso (backoff).

### 2. Atualização do `QueueService`
*   Adicionado suporte ao tipo `sqs` na inicialização do backend.
*   Validação de configuração obrigatória (`QUEUE_SQS_QUEUE_URL`) ao selecionar o backend SQS.

### 3. Configuração
*   Adicionados novos campos em `QueueSettings` (`src/core/config/settings.py`):
    *   `sqs_queue_url`
    *   `aws_region`
    *   `aws_access_key_id`
    *   `aws_secret_access_key`
*   Atualizado `.env.example` com as variáveis necessárias (`QUEUE_SQS_QUEUE_URL`, etc).

## Como Usar

1.  Instalar dependências (já incluídas): `boto3`.
2.  Configurar variáveis de ambiente no `.env`:
    ```env
    QUEUE_BACKEND=sqs
    QUEUE_SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/my-production-queue
    QUEUE_AWS_REGION=us-east-1
    QUEUE_AWS_ACCESS_KEY_ID=AKIA...
    QUEUE_AWS_SECRET_ACCESS_KEY=secret...
    ```
    *Nota: Se rodando em EC2/EKS com Role IAM, as chaves de acesso podem ser omitidas (o `boto3` detectará automaticamente).*

3.  Rodar o Worker:
    ```bash
    python3 -m src.core.queue.worker
    ```

## Detalhes Técnicos
*   **Long Polling**: O consumidor fica bloqueado por até 5 segundos esperando mensagens no SQS, o que é mais eficiente que polling constante.
*   **Idempotência de Processamento**: O `ReceiptHandle` é dinâmico e muda a cada recebimento. A abstração interna cuida dessa complexidade substituindo o ID estático da mensagem pelo Handle temporário durante o processamento.
*   **Segurança**: Credenciais são passadas via variáveis de ambiente, seguindo as melhores práticas (Twelve-Factor App).

## Próximos Passos
*   Configurar Dead Letter Queue (DLQ) diretamente no console da AWS para lidar com mensagens envenenadas (poison pills) que excedam o `maxReceiveCount`.
*   Monitorar métricas via CloudWatch (ApproximateNumberOfMessagesVisible, AgeOfOldestMessage).
