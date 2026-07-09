"""The engine I/O DTOs — the messages exchanged between the frontend/API and the
runtime engine.

These live here (not in owlprocessor) so the API and the Stage-2 engine worker
share one definition without either importing the engine package. owlprocessor's
``communication`` module re-exports these for backward compatibility, so engine
internals keep importing them unchanged.
"""

from typing import Literal

from pydantic import BaseModel


class AppExchangeGetOutput(BaseModel):
    """Data sent from the backend to the frontend.

    When the frontend has to render a form, ``message_content`` carries the
    JSONForm schema/uischema; otherwise it carries a notification/message.
    """

    message_type: Literal["layout", "notification", "information", "error"]
    layout_type: Literal["form", "message-box", ""]
    message_content: dict
    output_knowledge_graph: str


class AppExchangeFrontEndData(BaseModel):
    """Data sent from the frontend to the backend."""

    message_type: str
    message_content: dict
