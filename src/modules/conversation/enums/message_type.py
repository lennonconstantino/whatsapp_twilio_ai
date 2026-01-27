from enum import Enum


class MessageType(Enum):
    """
    Enum to classify message content type.

    Defines the format and type of message content:
    - TEXT: Simple text message
    - IMAGE: Message containing image
    - AUDIO: Audio/voice message
    - VIDEO: Video message
    - DOCUMENT: Document message
    """

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"

    def __repr__(self) -> str:
        return f"MessageType.{self.name}"
