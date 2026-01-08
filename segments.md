
Segments (Segmentos) são as "partes" em que uma mensagem é dividida para cobrança e envio. É basicamente como a Twilio conta quantas "unidades de mensagem" você usou.
Como funciona:
SMS:

- 1 segmento = até 160 caracteres (alfabeto latino básico - GSM-7)
- 1 segmento = até 70 caracteres (com emojis ou caracteres especiais - UCS-2)
- Mensagens maiores são divididas em múltiplos segmentos
- Exemplo: SMS com 320 caracteres = 2 segmentos

WhatsApp:

- 1 segmento = geralmente a mensagem inteira (até 4096 caracteres)
- WhatsApp cobra por "conversa" e não por segmento como SMS
- No seu caso: 1 segment = 1 mensagem WhatsApp

Exemplos práticos:
```text
📱 SMS (160 chars cada):
"Olá!" → 1 segmento
"Olá! 😊" → 1 segmento (mas limite cai pra 70 por causa do emoji)
[Texto de 180 chars] → 2 segmentos
[Texto de 500 chars] → 4 segmentos

💬 WhatsApp:
"Mensagem curta" → 1 segmento
"Mensagem de 3000 caracteres..." → 1 segmento
Imagem → 1 segmento
```

Por que importa:

- Custo: Você paga por segmento enviado
- SMS: Mais segmentos = mais caro
- WhatsApp: Cobra por "conversa de 24h", não por segmento individual

No seu log mostra 1 segment porque foi uma mensagem WhatsApp simples. Se fosse um SMS longo, você veria 2, 3, 4+ segmentos.