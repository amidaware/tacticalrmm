import asyncio
import json
import re
import secrets
import string
import traceback
from typing import TYPE_CHECKING, Any

import websockets

from accounts.utils import is_superuser
from tacticalrmm.constants import TRMM_WS_MAX_SIZE
from tacticalrmm.logger import logger

if TYPE_CHECKING:
    from accounts.models import User

# mesh users created by trmm: user//<username>___<pk>
MESH_USER_PATTERN = re.compile(r"(user//)?.*___\d+")


def build_mesh_display_name(
    *, first_name: str | None, last_name: str | None, company_name: str | None
) -> str:
    ret = ""
    if first_name:
        ret += first_name

    if last_name:
        ret += f" {last_name}"

    if ret and company_name:
        ret += f" - {company_name}"
    elif company_name:
        ret += company_name

    return ret


def has_mesh_perms(*, user: "User") -> bool:
    if user.is_superuser or is_superuser(user):
        return True

    return user.role and getattr(user.role, "can_use_mesh")


def has_full_agent_access(*, user: "User") -> bool:
    """True when the user can see every agent (superuser, or a role without client/site limits).

    These users get one link to the mesh device group instead of one link per device.
    """
    if user.is_superuser or is_superuser(user):
        return True

    role = user.role
    if not role:
        return False

    return not role.can_view_clients.exists() and not role.can_view_sites.exists()


def make_mesh_password() -> str:
    alpha = string.ascii_letters + string.digits
    nonalpha = "!@#$"
    passwd = [secrets.choice(alpha) for _ in range(29)] + [secrets.choice(nonalpha)]
    secrets.SystemRandom().shuffle(passwd)
    return "".join(passwd)


def transform_trmm(obj):
    ret = []
    try:
        for node in obj:
            node_id = node["node_id"]
            user_ids = [link["_id"] for link in node["links"]]
            ret.append({"node_id": node_id, "user_ids": user_ids})
    except Exception:
        logger.debug(traceback.format_exc)
    return ret


def transform_mesh(obj):
    pattern = re.compile(r".*___\d+")
    ret = []
    try:
        for _, nodes in obj.items():
            for node in nodes:
                node_id = node["_id"]
                try:
                    user_ids = [
                        user_id
                        for user_id in node["links"].keys()
                        if pattern.match(user_id)
                    ]
                except KeyError:
                    # will trigger on initial sync cuz no mesh users yet
                    # also triggers for invalid agents after sync
                    pass
                else:
                    ret.append({"node_id": node_id, "user_ids": user_ids})

    except Exception:
        logger.debug(traceback.format_exc)
    return ret


class MeshSync:
    def __init__(self, uri: str):
        self.uri = uri
        self.mesh_users = self.get_trmm_mesh_users()  # full list

    def mesh_action(
        self, *, payload: dict[str, Any], wait=True
    ) -> dict[str, Any] | None:
        async def _do(payload):
            async with websockets.connect(self.uri, max_size=TRMM_WS_MAX_SIZE) as ws:
                await ws.send(json.dumps(payload))
                if wait:
                    while 1:
                        try:
                            message = await asyncio.wait_for(ws.recv(), 120)
                            r = json.loads(message)
                            if r["action"] == payload["action"]:
                                return r
                        except asyncio.TimeoutError:
                            logger.error("Timeout reached.")
                            return None
                else:
                    return None

        payload["responseid"] = "meshctrl"
        logger.debug(payload)

        return asyncio.run(_do(payload))

    def get_unique_mesh_users(
        self, trmm_agents_list: list[dict[str, Any]]
    ) -> list[str]:
        userids = [i["links"] for i in trmm_agents_list]
        all_ids = [item["_id"] for sublist in userids for item in sublist]
        return list(set(all_ids))

    def get_trmm_mesh_users(self):
        payload = {"action": "users"}
        ret = {
            i["_id"]: i
            for i in self.mesh_action(payload=payload, wait=True)["users"]
            if re.search(r".*___\d+", i["_id"])
        }
        return ret

    def add_users_to_node(self, *, node_id: str, user_ids: list[str]):

        payload = {
            "action": "adddeviceuser",
            "nodeid": node_id,
            "usernames": [s.replace("user//", "") for s in user_ids],
            "rights": 4088024,
            "remove": False,
        }
        self.mesh_action(payload=payload, wait=False)

    def delete_users_from_node(self, *, node_id: str, user_ids: list[str]):
        payload = {
            "action": "adddeviceuser",
            "nodeid": node_id,
            "userids": user_ids,
            "rights": 0,
            "remove": True,
        }
        self.mesh_action(payload=payload, wait=False)

    def get_meshes(self) -> list[dict[str, Any]]:
        r = self.mesh_action(payload={"action": "meshes"}, wait=True)
        return r["meshes"] if r else []

    def add_users_to_mesh_group(self, *, mesh_id: str, user_ids: list[str]) -> None:
        payload = {
            "action": "addmeshuser",
            "meshid": mesh_id,
            "userids": user_ids,
            "meshadmin": 4088024,
        }
        self.mesh_action(payload=payload, wait=True)

    def remove_user_from_mesh_group(self, *, mesh_id: str, user_id: str) -> None:
        payload = {
            "action": "removemeshuser",
            "meshid": mesh_id,
            "userid": user_id,
        }
        self.mesh_action(payload=payload, wait=True)

    def update_mesh_displayname(self, *, user_info: dict[str, Any]) -> None:
        payload = {
            "action": "edituser",
            "id": user_info["_id"],
            "realname": user_info["full_name"],
        }
        self.mesh_action(payload=payload, wait=False)

    def add_user_to_mesh(self, *, user_info: dict[str, Any]) -> None:
        payload = {
            "action": "adduser",
            "username": user_info["username"],
            "email": user_info["email"],
            "pass": make_mesh_password(),
            "resetNextLogin": False,
            "randomPassword": False,
            "removeEvents": False,
            "emailVerified": True,
        }
        self.mesh_action(payload=payload, wait=False)
        if user_info["full_name"]:
            self.update_mesh_displayname(user_info=user_info)

    def delete_user_from_mesh(self, *, mesh_user_id: str) -> None:
        payload = {
            "action": "deleteuser",
            "userid": mesh_user_id,
        }
        self.mesh_action(payload=payload, wait=False)
