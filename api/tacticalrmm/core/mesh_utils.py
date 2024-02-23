import asyncio
import json
from typing import TYPE_CHECKING, Any

import websockets

from accounts.utils import is_superuser
from tacticalrmm.helpers import make_random_password
from tacticalrmm.logger import logger

if TYPE_CHECKING:
    from accounts.models import User


def mesh_action(
    *, payload: dict[str, Any], uri: str, wait=True
) -> dict[str, Any] | None:
    async def _do(payload, uri: str):
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps(payload))
            if wait:
                async for message in ws:
                    r = json.loads(message)
                    if r["action"] == payload["action"]:
                        return r
            else:
                return None

    payload["responseid"] = "meshctrl"
    logger.debug(payload)

    return asyncio.run(_do(payload, uri))


def update_mesh_displayname(*, user_info: dict[str, Any], uri: str) -> None:
    payload = {
        "action": "edituser",
        "id": user_info["_id"],
        "realname": user_info["full_name"],
    }
    mesh_action(payload=payload, uri=uri, wait=False)
    logger.debug(
        f"Updating user {user_info['username']} display name to: {user_info['full_name']}"
    )


def add_user_to_mesh(*, user_info: dict[str, Any], uri: str) -> None:
    payload = {
        "action": "adduser",
        "username": user_info["username"],
        "email": user_info["email"],
        "pass": make_random_password(len=30),
        "resetNextLogin": False,
        "randomPassword": False,
        "removeEvents": False,
    }
    mesh_action(payload=payload, uri=uri, wait=False)
    logger.debug(f"Adding user {user_info['username']} to mesh")
    if user_info["full_name"]:
        update_mesh_displayname(user_info=user_info, uri=uri)


def delete_user_from_mesh(*, mesh_user_id: str, uri: str) -> None:
    logger.debug(f"Deleting {mesh_user_id} from mesh")
    payload = {
        "action": "deleteuser",
        "userid": mesh_user_id,
    }
    mesh_action(payload=payload, uri=uri, wait=False)


def add_agent_to_user(*, user_id: str, node_id: str, hostname: str, uri: str) -> None:
    logger.debug(f"Adding agent {hostname} to {user_id}")
    payload = {
        "action": "adddeviceuser",
        "nodeid": node_id,
        "userids": [user_id],
        "rights": 72,
        "remove": False,
    }
    mesh_action(payload=payload, uri=uri, wait=False)


def remove_agent_from_user(*, user_id: str, node_id: str, uri: str) -> None:
    logger.debug(f"Removing agent {node_id} from {user_id}")
    payload = {
        "action": "adddeviceuser",
        "nodeid": node_id,
        "userids": [user_id],
        "rights": 0,
        "remove": True,
    }
    mesh_action(payload=payload, uri=uri, wait=False)


def has_mesh_perms(*, user: "User") -> bool:
    if user.is_superuser or is_superuser(user):
        return True

    return user.role and getattr(user.role, "can_use_mesh")


def get_mesh_users(*, uri: str) -> dict[str, Any] | None:
    payload = {"action": "users"}
    return mesh_action(payload=payload, uri=uri, wait=True)
