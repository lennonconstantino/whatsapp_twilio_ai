import json
import os
import argparse
import requests
from dotenv import load_dotenv
from twilio.rest import Client
from xml.etree import ElementTree as ET
from src.config import settings

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID' , 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'd0xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '+14155238886')

def send_via_twilio(message: str, to_number: str, media_url: str = None):
    """Envia mensagem via Twilio"""
    try:
        account_sid = TWILIO_ACCOUNT_SID
        auth_token = TWILIO_AUTH_TOKEN
        from_number = TWILIO_PHONE_NUMBER
        
        client = Client(account_sid, auth_token)
        
        kwargs = {
            'body': message,
            'from_': f'whatsapp:{from_number}',
            'to': f'whatsapp:{to_number}',
        }
        
        if media_url:
            kwargs['media_url'] = [media_url]
        
        msg = client.messages.create(**kwargs)
        print(f" Mensagem enviada via Twilio!")
        print(f"  SID: {msg.sid}")
        print(f"  Para: {to_number}")
        return msg
        
    except KeyError as e:
        print(f" Erro: Variável de ambiente faltando: {e}")
        return None
    except Exception as e:
        print(f" Erro ao enviar via Twilio: {e}")
        return None


def build_webhook_payload(message: str, media_url: str = None):
    """Constrói payload simulando webhook do Twilio"""
    payload = {
        'MessageSid': f'SM_local_{os.urandom(16).hex()}',
        'SmsMessageSid': f'SM_local_{os.urandom(16).hex()}',
        'AccountSid': os.environ.get('TWILIO_ACCOUNT_SID', 'AC_test'),
        'Body': message,
        'MessageType': 'text',
        'From': f"whatsapp:{os.environ.get('TWILIO_PHONE_NUMBER', '+14155238886')}",
        'To': f"whatsapp:{os.environ.get('MY_PHONE_NUMBER', '+5511999999999')}",
        'WaId': os.environ.get('TWILIO_PHONE_NUMBER', '+14155238886').replace('+', ''),
        'ProfileName': 'Local Test User',
        'NumMedia': '0',
        'NumSegments': '1',
        'SmsStatus': 'received',
        'ApiVersion': '2010-04-01',
        'LocalSender': 'True'
    }
    
    if media_url:
        payload['NumMedia'] = '1' # Quando o numero de caracteres de mensagens for menor que 160
        payload['MediaUrl0'] = media_url
        
        # Detectar tipo de mídia
        media_types = {
            ('.jpg', '.jpeg', '.png', '.gif', '.webp'): 'image/jpeg', 
            ('.mp4', '.avi', '.mov'): 'video/mp4',
            ('.ogg', '.mp3', '.wav'): 'audio/ogg',
            ('.pdf',): 'application/pdf'
        }
        
        content_type = 'application/octet-stream'
        for extensions, mime_type in media_types.items():
            if media_url.lower().endswith(extensions):
                content_type = mime_type
                break
        
        payload['MediaContentType0'] = content_type
    
    return payload


def send_to_local_webhook(message: str, media_url: str = None, port: int = 8080):
    """Envia para webhook local (simula Twilio)"""
    url = f'http://localhost:{port}/webhooks/twilio/inbound'
    payload = build_webhook_payload(message, media_url)
    headers = {
        "X-API-Key": os.getenv("INTERNAL_API_KEY")  # ← Sua própria chave
    }
    
    print(f"\n→ Enviando para webhook local...")
    print(f"  URL: {url}")
    print(f"  Mensagem: {message}")
    if media_url:
        print(f"  Mídia: {media_url}")
    
    try:
        response = requests.post(url, data=payload, timeout=30)
        
        print(f"\n Webhook respondeu!")
        print(f"  Status: {response.status_code}")
        
        return response
        
    except requests.exceptions.ConnectionError:
        print(f"\n Erro: Server não está rodando na porta {port}")
        print(f"  Execute: python server.py")
        return None
    except Exception as e:
        print(f"\n Erro: {e}")
        return None

def extract_response_message(response_text: str):
    """Extrai mensagem da resposta JSON"""
    try:
        data = json.loads(response_text)
        
        # Estrutura do TwilioWebhookResponseDTO
        if 'message' in data:
            return data['message']
        
        print(f" Resposta JSON não contém 'message': {data}")
        return None
        
    except json.JSONDecodeError as e:
        print(f" Erro ao parsear JSON: {e}")
        print(f"  Conteúdo recebido: {response_text[:500]}")
        return None

def extract_twiml_response(response_text: str):
    """Extrai mensagem do TwiML"""
    try:
        root = ET.fromstring(response_text)
        message_elements = root.findall('.//Message/Body')
        
        if message_elements and message_elements[0].text:
            return message_elements[0].text
        return None
        
    except ET.ParseError as e:
        print(f" Erro ao parsear TwiML: {e}")
        return None


def process_local_mode(message: str, media_url: str, port: int, to_number: str):
    """Processa modo local: webhook + Twilio"""
    
    # 1. Enviar para webhook local
    response = send_to_local_webhook(message, media_url, port)
    if not response:
        return
    
    # 2. Extrair resposta do webhook
    response_text = extract_response_message(response.text)
    
    if not response_text:
        print(" Nenhuma mensagem na resposta do webhook")
        return
    
    print(f"\n Resposta do webhook: {response_text}")
    
    # 3. Enviar resposta via Twilio
    # if not to_number:
    #     to_number = os.environ.get('MY_PHONE_NUMBER')
    #     if not to_number:
    #         print(" Erro: Número de destino não informado (use --to ou configure MY_PHONE_NUMBER)")
    #         return
    
    # print(f"\n→ Enviando resposta via Twilio...")
    # send_via_twilio(message=response_text, to_number=to_number)


def main():
    parser = argparse.ArgumentParser(
        description='Enviar mensagem WhatsApp via Twilio',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Modo local (webhook + Twilio)
  python send_message.py "Olá!" --to +5511999999999 --local
  python send_message.py "Teste" --to +5511999999999 --media https://picsum.photos/200 --local
  
  # Modo direto (apenas Twilio)
  python send_message.py "Olá!" --to +5511999999999
  python send_message.py "Teste" --to +5511999999999 --media https://picsum.photos/200
        """
    )
    
    parser.add_argument('message', help='Mensagem a enviar')
    parser.add_argument('--to', help='Número de destino (ex: +5511999999999)')    
    parser.add_argument('--media', '-m', help='URL da mídia (imagem, áudio, vídeo, PDF)')
    parser.add_argument('--local', action='store_true', help='Enviar para webhook local antes do Twilio')
    parser.add_argument('--port', type=int, default=settings.api.port, help='Porta do servidor local (padrão: 8000)')

    args = parser.parse_args()
    
    # Validar que tem número de destino
    if not args.local and not args.to:
        print(" Erro: Informe o número de destino com --to")
        parser.print_help()
        return
    
    # Executar modo apropriado
    if args.local:
        process_local_mode(
            message=args.message,
            media_url=args.media,
            port=args.port,
            to_number=args.to
        )
    else:
        send_via_twilio(
            message=args.message,
            to_number=args.to,
            media_url=args.media
        )


if __name__ == "__main__":
    main()