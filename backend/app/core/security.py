from fastapi import HTTPException, Request, status

from app.core.config import get_settings

# Headers added by tunnels and reverse proxies (ngrok and Cloud Run set X-Forwarded-For).
FORWARDED_HEADERS = ("x-forwarded-for", "x-forwarded-host", "forwarded")


def require_dashboard_access(request: Request) -> None:
    """Guard for the dashboard/CRM APIs.

    Hosted public demo (PUBLIC_DEMO=true): open on purpose. The data is fictional,
    resets automatically, and the UI warns visitors not to enter real details.

    Local development: only the Vapi webhook should be reachable through the
    ngrok tunnel. `fastapi dev` listens on localhost only, so any request that
    was proxied came from the internet and is refused.
    """
    if get_settings().public_demo:
        return
    if any(h in request.headers for h in FORWARDED_HEADERS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Dashboard API is local-only")
