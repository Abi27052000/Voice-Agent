from pydantic import BaseModel


class VapiPublicConfig(BaseModel):
    """Everything the browser needs to start a web call. Contains no secrets."""

    public_key: str
    assistants: dict[str, str]
    squads: dict[str, str] = {}
    # Vapi assistant name -> persona name, so the UI can label who is speaking.
    personas: dict[str, str] = {}
