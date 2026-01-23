import json
import os
import argparse
import requests
from dotenv import load_dotenv
from twilio.rest import Client
from xml.etree import ElementTree as ET
try:
    # Allow running as script without package context
    from src.core.config import settings  # type: ignore
except ModuleNotFoundError:
    settings = None

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID' , 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'd0xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
TWILIO_PHONE_NUMBER = "+17654361686"
#TWILIO_PHONE_NUMBER = "+15557657342"

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
            #'from_': f'{from_number}',
            #'to': f'{to_number}',            
        }
        
        if media_url:
            kwargs['media_url'] = [media_url]
        
        msg = client.messages.create(**kwargs)
        print(f" Mensagem enviada via Twilio!")
        print(f"  SID: {msg.sid}")
        print(f"  Para: {to_number}")
        print(f"  Mensagem: {msg.status} {msg.body} {msg.account_sid} {msg.direction} {msg.error_message}")
        return msg
        
    except KeyError as e:
        print(f" Erro: Variável de ambiente faltando: {e}")
        return None
    except Exception as e:
        print(f" Erro ao enviar via Twilio: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description='Enviar mensagem WhatsApp via Twilio',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Modo direto (apenas Twilio)
  python sender_test.py "Olá!" --to +5511999999999
  python sender_test.py "Teste" --to +5511999999999 --media https://picsum.photos/200
        """
    )
    
    parser.add_argument('message', help='Mensagem a enviar')
    parser.add_argument('--to', help='Número de destino (ex: +5511999999999)')    
    parser.add_argument('--media', '-m', help='URL da mídia (imagem, áudio, vídeo, PDF)')
    parser.add_argument('--port', type=int, default=settings.api.port, help='Porta do servidor local (padrão: 8000)')

    args = parser.parse_args()
    
    # Validar que tem número de destino
    if not args.to:
        print(" Erro: Informe o número de destino com --to")
        parser.print_help()
        return
        
    send_via_twilio(
        message=args.message,
        to_number=args.to,
        media_url=args.media
    )

if __name__ == "__main__":
    main()    
