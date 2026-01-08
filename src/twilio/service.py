
import time
from dto import MessageInfo
from entity import User
from helpers import TwilioHelpers
from payload import TwilioWhatsAppPayload
from validation import Validation

from twilio.twiml.messaging_response import MessagingResponse

class TwilioWhatsappService:
    def __init__(self):
        self.validation = Validation()
        self.feature = True
        self.user = None

    def user_authenticated(self, user: User):
        # TODO pegar do banco de dados de usuarios
        self.user = user
        return True

    def check(self):
        return self.validation.check()

    def __extract_media_content(self, payload: TwilioWhatsAppPayload) -> MessageInfo:
        # Mapeamento de tipos de mídia para respostas
        MEDIA_TYPE_MAP = {
            'audio':    ('audio', "Recebi seu áudio! 🎤"),
            'image':    ('image', "Recebi sua imagem! 📷"),
            'document': ('document', "Recebi seu documento! 📄"),
            'video':    ('video', "Recebi seu vídeo! 🎥"),
        }
        
        type = 'text'
        response_text = payload.body or ""
        path = None
        
        if payload.num_media > 0:
            # Identifica o tipo de mídia
            media_type = next(
                (media_type for media_type in MEDIA_TYPE_MAP if media_type in payload.media_content_type),
                'unknown'
            )
            
            if media_type in MEDIA_TYPE_MAP:
                type, response_text = MEDIA_TYPE_MAP[media_type]
            else:
                response_text = "Ops... Não reconheço esse formato!"

            # Download da mídia
            path = TwilioHelpers.download_media(payload.media_content_type, payload.media_url)

        return MessageInfo(message_input=payload.body, message_output=response_text, type=type, path=path)

    def __generate_response(self, message_info: MessageInfo) -> dict:
        response = ""

        # TODO construir integraçao com langgraph
        if self.feature: # and hasattr(self.feature, 'agent'):
            # response = feature.agent().run(message_info.input)
            response = TwilioHelpers.generate_response(message_info.output, self.user)
        else:
            response = TwilioHelpers.generate_response(message_info.output, self.user)

        return { "response" : response }

    def __send_media(self, path: str) -> MessagingResponse:
        response = MessagingResponse()
        reply = response.message()
        reply.media(path)
        return response


    def respond_and_send_message(self, payload: TwilioWhatsAppPayload):
		# Salvar requisição em banco de dados

        start_time = time.time()

        info = self.__extract_media_content(payload)
		
        response = self.__generate_response(info)

        if response["response"] in "path":
            self.__send_media("path")

		# Salvar resposta em banco de dados

		# Verificar se a conversa deve ser encerrada
        # try:
        #     intent_detector = ClosingIntentDetector()
        #     user_intent = intent_detector.analyze_intent(message_text)
        #     if user_intent.is_confirmational_close:
        #         self._team_force_close()
        # except Exception:
        #     pass        

		# Se chegou até aqui, deu bom
		# Returna as infos para WhatsApp Twilio
        conversation_id = "1"

        result = {
            "status": "success",
            "user": {
                #"first_name": getattr(user_authenticated, "first_name", "Unknown"),
                #"last_name": getattr(user_authenticated, "last_name", "User"),
                "profile_name": getattr(self.user, "profile_name", "Unknown"),
            },
            "conversation_id": conversation_id,
            "messages": [info.message_input, response["response"]],
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "whatsapp_api_result": {""},
        }

        return result
