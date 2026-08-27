"""Board Member auth stub. Only human user in MVP (Documents 14, 18)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from varma.config import get_settings

BOARD_MEMBER_IDENTITY = "board-member"


@dataclass
class Actor:
    identity: str
    actor_type: str  # board_member | employee | anonymous


def parse_actor(
    authorization: str | None = None,
    x_varma_actor: str | None = None,
    x_varma_employee: str | None = None,
) -> Actor:
    settings = get_settings()
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if token == settings.board_member_stub_token or x_varma_actor == BOARD_MEMBER_IDENTITY:
        return Actor(identity=BOARD_MEMBER_IDENTITY, actor_type="board_member")
    if x_varma_employee:
        return Actor(identity=x_varma_employee, actor_type="employee")
    return Actor(identity="anonymous", actor_type="anonymous")


def require_board_member(
    authorization: str | None = Header(default=None),
    x_varma_actor: str | None = Header(default=None),
) -> Actor:
    actor = parse_actor(authorization, x_varma_actor, None)
    if actor.actor_type != "board_member":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Board Member identity required")
    return actor
