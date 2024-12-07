from typing import Any

class FrontEndData:
    """
    This class represents the data which is sent from the frontend to the backend.
 
    """
    def __init__(self, message_type: str, message_content: Any) -> None:
        self.message_type: str = message_type 
        self.message_content : Any = message_content



class BackEndData:
    def __init__(self):
        self.message_type: str = None 
        self.message_content: Any = None

