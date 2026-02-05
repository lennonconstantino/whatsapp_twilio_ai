# Relatório de Correção: Resiliência a Falhas de AI

## Contexto
Conforme identificado na análise técnica (`research_04.md`, item 2), o sistema apresentava um risco de UX onde falhas no processamento do agente de AI (ex: timeout, erro de API do LLM, bug no código do agente) resultavam em silêncio total para o usuário. O log de erro era gerado no servidor, mas o usuário final ficava sem feedback.

## Problema
- **Silêncio em Falhas:** Se o método `agent_runner.run()` lançasse uma exceção, o fluxo era interrompido e nenhuma mensagem era enviada de volta.
- **Falta de Persistência:** Mesmo que um erro fosse capturado, não havia mecanismo padronizado para registrar que uma tentativa de resposta falhou.

## Solução Aplicada
Implementou-se um mecanismo de **Fallback com Resposta Amigável** dentro do worker de processamento de AI (`TwilioWebhookService.handle_ai_response`).

### Alterações Realizadas

#### 1. Centralização do Envio (`_send_and_persist_response`)
Arquivo: `src/modules/channels/twilio/services/twilio_webhook_service.py`

Foi criado um método auxiliar privado para encapsular a lógica de:
1.  Enviar mensagem via Twilio.
2.  Persistir a mensagem enviada no banco de dados (histórico da conversa).

Isso permitiu reutilizar a mesma lógica tanto para o sucesso (resposta da AI) quanto para o erro (mensagem de desculpas).

#### 2. Tratamento de Exceção (`try/except`)
O bloco `try/except` principal do método `handle_ai_response` foi expandido para capturar qualquer `Exception`.

```python
except Exception as e:
    logger.error("Error in AI background processing", error=str(e), correlation_id=correlation_id)
    
    # Send friendly error message
    error_message = "Desculpe, estou enfrentando dificuldades técnicas no momento. Por favor, tente novamente em alguns instantes."
    
    self._send_and_persist_response(
        owner_id=owner_id,
        conversation_id=conversation_id,
        sender_number=payload.to_number,
        recipient_number=payload.from_number,
        body=error_message,
        correlation_id=correlation_id,
        is_error=True
    )
```

#### 3. Rastreabilidade
As mensagens de erro enviadas são persistidas com um metadado adicional:
```python
metadata={
    # ...
    "is_error_fallback": True
}
```
Isso permite análises futuras sobre quantas vezes o fallback foi acionado.

## Impacto
- **Experiência do Usuário:** O usuário sempre receberá um feedback, mesmo no pior cenário de falha técnica.
- **Manutenibilidade:** Código de envio de mensagem refatorado e DRY (Don't Repeat Yourself).
- **Observabilidade:** Falhas são logadas e também registradas no histórico da conversa como mensagens do sistema.

## Próximos Passos
- Monitorar a métrica de mensagens com `is_error_fallback=True`.
- Considerar implementar um mecanismo de *retry* (fila de tentativas) antes de desistir e enviar a mensagem de erro, caso a falha seja transiente (ex: timeout de rede).
