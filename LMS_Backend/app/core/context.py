"""Request metadata passed from the web layer to services (for auditing)."""

from dataclasses import dataclass

from fastapi import Request

from app.core.logging import request_id_ctx

_MAX_USER_AGENT_LENGTH = 255


@dataclass(frozen=True)
class RequestMeta:
    """Who/where a request came from. All fields are optional (e.g. CLI usage)."""

    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None

    @classmethod
    def from_request(cls, request: Request) -> "RequestMeta":
        # Behind a reverse proxy, run uvicorn with --proxy-headers and
        # --forwarded-allow-ips so that request.client reflects the real client.
        user_agent = request.headers.get("user-agent")
        return cls(
            ip_address=request.client.host if request.client else None,
            user_agent=user_agent[:_MAX_USER_AGENT_LENGTH] if user_agent else None,
            request_id=request_id_ctx.get(),
        )


CLI_REQUEST = RequestMeta()
