from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Voice Agent API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Vapi: the private key stays on the server; the public key is safe for the browser.
    vapi_api_key: SecretStr | None = None
    vapi_public_key: str | None = None
    vapi_base_url: str = "https://api.vapi.ai"

    # Shared secret Vapi sends as "Authorization: Bearer <secret>" on webhook/tool calls.
    vapi_webhook_secret: SecretStr | None = None

    # Public HTTPS URL that tunnels to this backend (e.g. an ngrok static domain).
    public_base_url: str | None = None

    database_url: str = "sqlite:///./data/app.db"

    # The fictional business's local time zone (used for scheduling windows).
    business_timezone: str = "America/New_York"

    # --- Hosted demo (Cloud Run) ---
    # Public demo: dashboard/CRM APIs are intentionally open (fictional data that
    # resets), and the UI shows a "don't enter real info" banner. Off locally,
    # where those APIs are blocked for requests arriving through a tunnel.
    public_demo: bool = False
    # Seed demo bookings and win-back leads at startup when the database is empty.
    seed_demo_data: bool = False
    # Vapi resource IDs as JSON (same shape as vapi/ids.json, which is gitignored
    # and therefore not in the container).
    vapi_ids_json: str | None = None

    @property
    def webhook_url(self) -> str | None:
        if not self.public_base_url:
            return None
        return f"{self.public_base_url.rstrip('/')}{self.api_prefix}/vapi/webhook"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
