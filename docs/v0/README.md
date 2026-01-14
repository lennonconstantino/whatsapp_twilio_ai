# whatsapp_twilio_ai
whatsapp_twilio_ai

0. login your account
https://console.twilio.com

1. running server receive
```bash
python receive.py
```

2. running ngrok
```bash
ngrok http 8080
```

3. get webhook url https://2f581f2aa5ee.ngrok-free.app
![1766091013961](docs/image/README/1766091013961.png)

4. adding the webhook + '/whatsapp'
![1766091086351](docs/image/README/1766091086351.png)

---

# Uso
```python
# Flask
from flask import request

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        payload = TwilioWhatsAppPayload(**request.values)
        # Processar a mensagem
        process_message(payload)
        return '', 200
    except ValidationError as e:
        return {'error': str(e)}, 400

# FastAPI (ainda melhor!)
from fastapi import FastAPI, Form

@app.post('/webhook')
async def webhook(payload: TwilioWhatsAppPayload = Form(...)):
    # Validação automática!
    process_message(payload)
    return {'status': 'ok'}

# Uso
payload = TwilioWhatsAppPayload(**request.values)

# Agora channel_metadata já é um dict
if payload.channel_metadata:
    print(payload.channel_metadata['type'])  # 'whatsapp'

# E num_media é int
if payload.num_media > 0:
    print("Tem mídia anexada!")
```