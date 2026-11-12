from pydantic import BaseModel


class VapiPublicConfig(BaseModel):
    """Everything the browser needs to start a web call. Contains no secrets."""

    public_key: str
    assistants: dict[str, str]
    squads: dict[str, str] = {}
    # Vapi assistant name -> persona name, so the UI can label who is speaking.
    personas: dict[str, str] = {}
    # Hosted public demo: the UI shows a "fictional data, resets" notice.
    public_demo: bool = False
