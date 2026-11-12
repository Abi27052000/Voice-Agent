from pydantic import BaseModel


class VapiPublicConfig(BaseModel):
    """Everything the browser needs to start a web call. Contains no secrets."""

    public_key: str
    assistants: dict[str, str]
