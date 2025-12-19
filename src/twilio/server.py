import os
from pydantic import ValidationError
import requests
from flask import Flask, request, redirect
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from payload import TwilioWhatsAppPayload

app = Flask(__name__)

# TODO
# Modo Client ou Local - NOK 80%
# Variaveis de ambiente - NOK 90%
# Ajustar Exceptions - NOK 0%
# Refatorar Handler - NOK 0%
# Pegar do banco de dados de usuarios - NOK 0%
# Construir integraçao com langgraph - NOK 0%
# Implementar o modulo Conversations - NOK 0%

def download_audio(media_type, media_url):
    """Baixa o áudio do Twilio"""
    try:
        auth = (os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_AUTH_TOKEN'])
        audio_response = requests.get(media_url, auth=auth, timeout=50)
        
        # Verificar se o download foi bem-sucedido
        audio_response.raise_for_status()

        ext = media_type.split('/')[-1]
        filename = media_url.split('/')[-1] + "." + ext
        
        # Salvar localmente
        with open(filename, 'wb') as f:
            f.write(audio_response.content)
        
        print(f" Áudio salvo como {filename}")
        return filename
    except Exception as e:
        print(f" Erro ao baixar áudio: {e}")
        return None

def send_whatsapp_message(to_number: str, message: str, media_url: str = None):
    """Envia mensagem via Twilio Client (funciona em modo local)"""
    try:
        account_sid = os.environ['TWILIO_ACCOUNT_SID']
        auth_token = os.environ['TWILIO_AUTH_TOKEN']
        client = Client(account_sid, auth_token)
        
        from_whatsapp_number = 'whatsapp:' + os.environ['FROM_NUMBER']
        
        kwargs = {
            'body': message,
            'from_': from_whatsapp_number,
            'to': to_number
        }
        
        if media_url:
            kwargs['media_url'] = [media_url]
        
        msg = client.messages.create(**kwargs)
        print(f"Mensagem enviada via Twilio!")
        print(f"   SID: {msg.sid}")
        print(f"   Para: {to_number}")
    except Exception as e:
        print(f"Erro ao enviar: {e}")

def process_message(payload: TwilioWhatsAppPayload) -> MessagingResponse:
    if payload.body:
        print(f"body: {payload.body}")

    # Se for modo local (client_receive=True), envia via Twilio Client
    if payload.client_receive:
        print(f"\nEnviando resposta via Twilio Client...")
        send_whatsapp_message(
            to_number=payload.from_number,
            message=payload.body
        )
        # Retornar resposta vazia para o webhook local
        return MessagingResponse()

    # Modo normal: retorna TwiML para o Twilio processar
    response_text = "Está tudo ok!"

    # Extract Media Content Type
    if payload.num_media > 0:
        if 'audio' in payload.media_content_type:
            response_text = "Recebi seu áudio! 🎤"
            download_audio(payload.media_content_type, payload.media_url)
        elif 'image' in payload.media_content_type:
            response_text = "Recebi sua imagem! 📷"
        elif 'document' in payload.media_content_type:
            response_text = "Recebi seu documento! 📄"
        elif 'video' in payload.media_content_type:
            response_text = "Recebi seu vídeo! 🎥"
        else:
            response_text = "Ops... Não reconheço esse formato!"

    # se eu quiser mandar um midia como resposta
    # -> reply.media("path")
    response = MessagingResponse()
    reply = response.message()
    reply.body(response_text)
    return response

def verify_environment():
    # Verificar variáveis de ambiente
    required_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'FROM_NUMBER']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"  ATENÇÃO: Variáveis de ambiente faltando: {', '.join(missing_vars)}")
        print(f"   Configure-as no arquivo .env antes de usar o servidor")

@app.route("/whatsapp", methods=['GET', 'POST'])
def whatsapp_receive():
    """Respond to incoming calls with a simple text message."""
    # Fetch the message
    # Fetch_msg=request.form
    # print("Fetch_msg-->",Fetch_msg)

    try:
        # parse message
        payload = TwilioWhatsAppPayload(**request.values)
        # validation
        response = process_message(payload)

        return str(response), 200
    except ValidationError as e:
        return {'error': str(e)}, 400 
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return {'error': 'Internal server error'}, 500

@app.route("/health", methods=['GET'])
def health_check():
    """Endpoint de health check"""
    return {'status': 'ok'}, 200

if __name__ == "__main__":
    verify_environment()

    app.run(port=8080)