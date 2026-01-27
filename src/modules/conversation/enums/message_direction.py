from enum import Enum


class MessageDirection(Enum):
    """
    Enum for message direction.

    Defines the direction of message flow:
    - INBOUND: Message received by the system
    - OUTBOUND: Message sent to the client
    """

    INBOUND = "inbound"
    OUTBOUND = "outbound"

    def __repr__(self) -> str:
        return f"MessageDirection.{self.name}"
