
from entity import User
from payload import TwilioWhatsAppPayload
from service import TwilioWhatsappService


class TwilioHandler:
    def __init__(self, service: TwilioWhatsappService):
        self.service = service

    def process_handler(self, payload: TwilioWhatsAppPayload):
        if self.service.user_authenticated(user=User(id=payload.wa_id, profile_name=payload.profile_name, phone=payload.from_number)) is not True:
            return { "error - Unauthorized" : 401 }
                
        if self.service.check() is not True:
            return { "error - Unprocessable Entity" : 422 }
        
        return self.service.respond_and_send_message(payload)
