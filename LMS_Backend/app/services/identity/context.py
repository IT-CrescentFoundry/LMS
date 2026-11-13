"""Authenticated request context and acting-user representation."""

from dataclasses import dataclass

from app.models.identity import UserAccount, UserSession


@dataclass(frozen=True)
class Actor:
    """The user performing an administrative action, with their effective permissions."""

    user_id: int
    permissions: frozenset[str]


@dataclass(frozen=True)
class AuthContext:
    user: UserAccount
    session: UserSession
    permissions: frozenset[str]
    roles: tuple[str, ...]

    def has(self, permission: str) -> bool:
        return permission in self.permissions

    @property
    def actor(self) -> Actor:
        return Actor(user_id=self.user.id, permissions=self.permissions)
