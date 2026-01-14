
import os
import requests

from src.core.models.domain import User

class TwilioHelpers:
    """Helper para chamar funcoes utils de forma simples"""
    
    # TODO
    @staticmethod
    def download_media(media_type: str, media_url: str) -> str:
        """Baixa o media do Twilio"""
        try:
            auth = (os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_AUTH_TOKEN'])
            media_response = requests.get(media_url, auth=auth, timeout=50)
            
            # Verificar se o download foi bem-sucedido
            media_response.raise_for_status()

            type = media_type.split('/')[0]
            ext = media_type.split('/')[-1]
            filename = media_url.split('/')[-1] + "." + ext
            
            # Salvar localmente
            with open(filename, 'wb') as f:
                f.write(media_response.content)
            
            print(f" Media {type} salvo como {filename}")
            return filename
        except Exception as e:
            print(f" Erro ao baixar media: {e}")
            return None
        
    @staticmethod
    def generate_response(user_message: str, user: User) -> str:
        """
        Gera uma resposta para a mensagem do usuário
        """
        # Mock de resposta - substitua pela sua lógica
        responses = [
            f"Olá {user.first_name}! Recebi sua mensagem: '{user_message}'",
            "Como posso ajudá-lo hoje?",
            "Interessante! Me conte mais sobre isso.",
            "Entendi. Há mais alguma coisa que gostaria de saber?",
            "Obrigado pela mensagem. Vou processar isso para você."
        ]
        
        # Escolher resposta baseada no comprimento da mensagem (mock)
        response_index = len(user_message) % len(responses)
        return responses[response_index]
