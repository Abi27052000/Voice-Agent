from fastapi import HTTPException, Request, status

# Headers added by tunnels and reverse proxies (ngrok sets X-Forwarded-For).
FORWARDED_HEADERS = ("x-forwarded-for", "x-forwarded-host", "forwarded")


def require_direct_request(request: Request) -> None:
    """Block requests that arrive through the public tunnel.

    The webhook must be public (Vapi calls it via ngrok), but CRM data must not.
    `fastapi dev` only listens on localhost, so any request that wasn't proxied
    came from this machine. Replace with real auth before deploying publicly.
    """
    if any(h in request.headers for h in FORWARDED_HEADERS):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Dashboard API is local-only")
