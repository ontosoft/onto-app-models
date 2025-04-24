from typing import Literal

from pydantic import BaseModel

class AppExchangeGetOutput(BaseModel):
    """
    This class represents the data which is sent from the backend
    to the frontend. If the frontend has to show the form then
    an object of this class contains JSONForm elements to 
    create that form.
 
    """
    message_type: Literal[ "layout" , "notification" , "error"]
    layout_type: Literal[ "form" , "message-box"]
    message_content: dict


class AppExchangeFrontEndData(BaseModel):
    """
    This class represents the data which is sent from the frontend to the backend.
 
    """
    message_type: str
    message_content : dict 


