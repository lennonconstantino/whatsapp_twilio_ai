import os
import argparse
import requests
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()  # Carrega as variáveis do .env

def send_via_twilio(message: str, media_url: str = None, to_number: str = None):
    """Envia mensagem real via Twilio"""
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    client = Client(account_sid, auth_token)
    
    from_whatsapp_number = 'whatsapp:' + os.environ['FROM_NUMBER']
    
    if to_number:
        to_whatsapp_number = f'whatsapp:{to_number}'
    else:
        to_whatsapp_number = 'whatsapp:' + os.environ['MY_PHONE_NUMBER']

    kwargs = {
        'body': message,
        'from_': from_whatsapp_number,
        'to': to_whatsapp_number
    }
    
    if media_url:
        kwargs['media_url'] = [media_url]
    
    try:
        msg = client.messages.create(**kwargs)
        print(f"Mensagem enviada via Twilio!")
        print(f"   SID: {msg.sid}")
        return msg
    except Exception as e:
        print(f"Erro ao enviar: {e}")
        return None

def send_to_local_webhook(message: str, media_url: str = None, port: int = 8080):
    """Simula webhook do Twilio para o receive.py local"""
    
    # Simular dados que o Twilio enviaria
    payload = {
        'MessageSid': f'SM_local_{os.urandom(8).hex()}',
        'SmsMessageSid': f'SM_local_{os.urandom(8).hex()}',
        'AccountSid': os.environ.get('TWILIO_ACCOUNT_SID', 'AC_test'),
        'Body': message,
        'MessageType': 'text',
        'From': f"whatsapp:{os.environ.get('MY_PHONE_NUMBER', '+5511999999999')}",
        'To': f"whatsapp:{os.environ.get('FROM_NUMBER', '+14155238886')}",
        'WaId': os.environ.get('MY_PHONE_NUMBER', '5511999999999').replace('+', ''),
        'ProfileName': 'Client User',
        'NumMedia': '1' if media_url else '0',
        'NumSegments': '1',
        'SmsStatus': 'received',
        'ApiVersion': '2010-04-01',
        'ChannelMetadata': '{"type":"whatsapp","data":{"context":{"ProfileName":"Client User"}}}',
        'ClientReceive': True
    }
    
    # Adicionar mídia se fornecida
    if media_url:
        payload['MediaUrl0'] = media_url
        # Detectar tipo de mídia pela extensão
        if media_url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            payload['MediaContentType0'] = 'image/jpeg'
        elif media_url.endswith(('.mp4', '.avi', '.mov')):
            payload['MediaContentType0'] = 'video/mp4'
        elif media_url.endswith(('.ogg', '.mp3', '.wav')):
            payload['MediaContentType0'] = 'audio/ogg'
        elif media_url.endswith('.pdf'):
            payload['MediaContentType0'] = 'application/pdf'
        else:
            payload['MediaContentType0'] = 'application/octet-stream'
    
    print(f"\nEnviando para webhook local...")
    print(f"   URL: http://localhost:{port}/whatsapp")
    print(f"   Mensagem: {message}")
    if media_url:
        print(f"   Mídia: {media_url}")
    
    try:
        response = requests.post(
            f'http://localhost:{port}/whatsapp',
            data=payload,
            timeout=10
        )
        
        print(f"\nWebhook respondeu!")
        print(f"   Status: {response.status_code}")
        print(f"   Resposta: {response.text[:200]}")
        return response
        
    except requests.exceptions.ConnectionError:
        print(f"\n Erro: server.py não está rodando na porta {port}")
        print(f"   Execute: python server.py")
        return None
    except Exception as e:
        print(f"\n Erro: {e}")
        return None

def send_and_get_response(message: str, media_url: str = None, port: int = 8080):
    """Envia para webhook local E envia a resposta via Twilio"""
    
    print(f"\n Enviando para webhook local...")
    
    # 1. Simular webhook
    response = send_to_local_webhook(message, media_url, port)
    
    if not response:
        return
    
    # 2. Extrair resposta do TwiML
    try:
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.text)
        
        # Buscar a mensagem na resposta TwiML
        message_elements = root.findall('.//Message/Body')
        
        if message_elements:
            response_text = message_elements[0].text
            print(f"\n Resposta do webhook: {response_text}")
            
            # 3. Enviar essa resposta via Twilio
            print(f"\n Enviando resposta para WhatsApp...")
            send_via_twilio(
                message=response_text,
                to_number=os.environ.get('MY_PHONE_NUMBER')
            )
        else:
            print("  Nenhuma mensagem na resposta")
            
    except Exception as e:
        print(f" Erro ao processar resposta: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Enviar mensagem WhatsApp (real ou local para debug)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Enviar para webhook local Client
  python send_message.py "Olá, teste!" --local
  python send_message.py "Teste com imagem" --media https://picsum.photos/200 --local
  
  # Enviar via Twilio (real) direto
  python send_message.py "Olá, teste!" --to +5511999999999
  python send_message.py "Teste com imagem" --media https://picsum.photos/200 --to +5511999999999
        """
    )
    
    parser.add_argument(
        'message',
        help='Mensagem a enviar'
    )
    
    parser.add_argument(
        '--media',
        '-m',
        help='URL da mídia (imagem, áudio, vídeo, PDF)'
    )
    
    parser.add_argument(
        '--to',
        help='Número de destino (ex: +5511999999999) - envia via Twilio'
    )
    
    parser.add_argument(
        '--local',
        action='store_true',
        help='Enviar para webhook local (server.py) e depois twilio'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Porta do receive.py (padrão: 8080)'
    )

    args = parser.parse_args()
    
    # Decidir qual método usar
    if args.local:
        # Modo client: enviar para receive.py local
        send_and_get_response(
            message=args.message,
            media_url=args.media,
            port=args.port
        )
    elif args.to:
        # Modo produção: enviar via Twilio
        send_via_twilio(
            message=args.message,
            media_url=args.media,
            to_number=args.to
        )
    else:
        print("Erro: Use --local para debug ou --to NUMERO para enviar via Twilio")
        parser.print_help()
