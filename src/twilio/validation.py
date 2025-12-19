from payload import TwilioWhatsAppPayload

class TwilioValidation:
    def __init__(self, payload: TwilioWhatsAppPayload):
        self.payload = payload

    def check(self):
        self.__is_message_too_old()
        self.__get_owner_number_phone()
        self.__get_customer_number_phone()

        return True
        
    def __is_message_too_old(self):
        pass
    
    def __get_owner_number_phone(self):
        # message.to_    # owner_number
        pass

    def __get_customer_number_phone(self): 
        # message.from_  # customer_number ou WaId
        pass