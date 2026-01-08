import os
from pydantic import ValidationError
import requests
from dotenv import load_dotenv
from flask import Flask, request, redirect
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from payload import TwilioWhatsAppPayload

load_dotenv()

DEBUG = True

app = Flask(__name__)

# TODO
# Modo Client ou Local - NOK 80%
# Variaveis de ambiente - NOK 90%
# Ajustar Exceptions - NOK 0%
# Refatorar Handler - NOK 0%
# Pegar do banco de dados de usuarios - NOK 0%
# Construir integraçao com langgraph - NOK 0%
# Implementar o modulo Conversations - NOK 0%

def verify_environment():
    required_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'FROM_NUMBER']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"⚠️  Variáveis faltando: {', '.join(missing_vars)}")
        return False

    return True

# TODO
def download_audio(media_type: str, media_url: str) -> str:
    """Baixa o áudio do Twilio"""
    try:
        auth = (os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_AUTH_TOKEN'])
        audio_response = requests.get(media_url, auth=auth, timeout=50)
        audio_response.raise_for_status()

        ext = media_type.split('/')[-1]
        filename = media_url.split('/')[-1] + "." + ext
        
        with open(filename, 'wb') as f:
            f.write(audio_response.content)
        
        print(f" Áudio salvo como {filename}")
        return filename
    except Exception as e:
        print(f" Erro ao baixar áudio: {e}")
        return None

def send_via_client(to_number: str, message: str):
    """Envia mensagem via Twilio Client (bypass TwiML)"""
    try:
        account_sid = os.environ['TWILIO_ACCOUNT_SID']
        auth_token = os.environ['TWILIO_AUTH_TOKEN']
        from_number = os.environ['FROM_NUMBER']
        
        client = Client(account_sid, auth_token)
        
        # Garante que ambos os números têm o prefixo whatsapp:
        if not to_number.startswith('whatsapp:'):
            to_number = f'whatsapp:{to_number}'
        
        if not from_number.startswith('whatsapp:'):
            from_number = f'whatsapp:{from_number}'

        print("--> " + from_number)
        
        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number,
        )
        
        print(f" Enviado via Client! SID: {msg.sid}")
        return msg
        
    except Exception as e:
        print(f" Erro ao enviar via Client: {e}")
        return None

def process_message(payload: TwilioWhatsAppPayload) -> MessagingResponse:
    """Processa mensagem recebida"""
    if DEBUG:
        print(f"\n📩 Mensagem recebida:")
        print(f"   De: {payload.from_number}")
        print(f"   Para: {payload.to_number}")
        print(f"   Body: {payload.body}")
    
    # OPÇÃO 1: Usar Client (bypass TwiML para evitar 63005)
    if payload.client_receive:
        print(f" Enviando via Client...")
        send_via_client(payload.from_number, payload.body)
        # Retorna resposta vazia para o webhook
        return MessagingResponse()

    response_text = "Ola"
    
    # Processa mídia
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
        
    # OPÇÃO 2: Tentar via TwiML (padrão)
    # se eu quiser mandar um midia como resposta
    # -> reply.media("path")
    response = MessagingResponse()
    reply = response.message()
    reply.body(response_text)
    return response

@app.route("/whatsapp", methods=['POST'])
def whatsapp_receive():
    """Recebe mensagens do WhatsApp"""
    try:
        payload = TwilioWhatsAppPayload(**request.values)
        response = process_message(payload)
        
        twiml_str = str(response)
        return twiml_str, 200, {'Content-Type': 'text/xml'}
        
    except ValidationError as e:
        print(f" Erro de validação: {e}")
        return {'error': str(e)}, 400
    except Exception as e:
        print(f" Erro inesperado: {e}")
        return {'error': 'Internal server error'}, 500

@app.route("/health", methods=['GET'])
def health_check():
    """Health check"""
    return {'status': 'ok'}, 200

if __name__ == "__main__":
    if verify_environment():
        app.run(port=8080)