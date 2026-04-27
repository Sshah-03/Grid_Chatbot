from pydantic import BaseModel, Field


class IncomingWebSocketMessage(BaseModel):
    type: str
    body: str | None = Field(default=None, max_length=4000)
    client_message_id: str | None = None
