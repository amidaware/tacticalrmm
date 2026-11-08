from unittest.mock import MagicMock, patch

from django.test import override_settings
from model_bakery import baker

from accounts.models import User
from core.mesh_utils import has_full_agent_access
from core.tasks import sync_mesh_perms_task
from tacticalrmm.test import TacticalTestCase

MESH_ID = "mesh//testgroup"


class TestMeshSyncGroupRights(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.site = baker.make("clients.Site")
        self.other_site = baker.make("clients.Site")
        self.agent1 = baker.make_recipe(
            "agents.agent", site=self.site, mesh_node_id="ab" * 48
        )
        self.agent2 = baker.make_recipe(
            "agents.agent", site=self.other_site, mesh_node_id="cd" * 48
        )
        self.node1 = f"node//{self.agent1.hex_mesh_node_id}"
        self.node2 = f"node//{self.agent2.hex_mesh_node_id}"

        self.admin = User.objects.create_user(username="admin", is_superuser=True)

        full_role = baker.make("accounts.Role", can_use_mesh=True)
        self.tech = User.objects.create_user(username="tech", role=full_role)

        limited_role = baker.make("accounts.Role", can_use_mesh=True)
        limited_role.can_view_sites.set([self.site])
        self.limited = User.objects.create_user(username="limited", role=limited_role)

        no_mesh_role = baker.make("accounts.Role", can_use_mesh=False)
        self.nomesh = User.objects.create_user(username="nomesh", role=no_mesh_role)

    def _run(self, *, node_links: dict, group_links: dict, mesh_users: dict):
        ms = MagicMock()
        ms.mesh_users = mesh_users
        ms.mesh_action.return_value = {
            "nodes": {
                MESH_ID: [
                    {"_id": node_id, "links": links}
                    for node_id, links in node_links.items()
                ]
            }
        }
        ms.get_meshes.return_value = [{"_id": MESH_ID, "links": group_links}]
        ms.get_unique_mesh_users.return_value = []
        with (
            patch("core.tasks.MeshSync", return_value=ms),
            patch("core.tasks.get_mesh_ws_url", return_value="ws://mesh"),
            patch("core.tasks.sleep"),
        ):
            sync_mesh_perms_task()
        return ms

    def _calls(self, mock, name):
        return [c.kwargs for c in getattr(mock, name).call_args_list]

    def test_has_full_agent_access(self):
        self.assertTrue(has_full_agent_access(user=self.admin))
        self.assertTrue(has_full_agent_access(user=self.tech))
        self.assertFalse(has_full_agent_access(user=self.limited))

    def test_full_access_users_get_group_link_not_device_links(self):
        ms = self._run(node_links={}, group_links={}, mesh_users={})

        # every mesh user is created, including the ones that only get the group link
        created = {c["user_info"]["_id"] for c in self._calls(ms, "add_user_to_mesh")}
        self.assertEqual(
            created,
            {
                self.admin.mesh_user_id,
                self.tech.mesh_user_id,
                self.limited.mesh_user_id,
            },
        )

        # only the limited user gets a per-device link, and only on its site
        added = self._calls(ms, "add_users_to_node")
        self.assertEqual(
            added, [{"node_id": self.node1, "user_ids": [self.limited.mesh_user_id]}]
        )

        # users created in this run get the group link on the next run
        ms.add_users_to_mesh_group.assert_not_called()

    def test_group_link_added_for_existing_users(self):
        links = {self.limited.mesh_user_id: {"rights": 4088024}}
        ms = self._run(
            node_links={self.node1: links, self.node2: {}},
            group_links={},
            mesh_users={
                self.admin.mesh_user_id: {},
                self.tech.mesh_user_id: {},
                self.limited.mesh_user_id: {},
            },
        )
        ms.add_user_to_mesh.assert_not_called()
        group_adds = self._calls(ms, "add_users_to_mesh_group")
        self.assertEqual(len(group_adds), 1)
        self.assertEqual(group_adds[0]["mesh_id"], MESH_ID)
        self.assertEqual(
            set(group_adds[0]["user_ids"]),
            {self.admin.mesh_user_id, self.tech.mesh_user_id},
        )

    def test_full_access_users_are_not_deleted_from_mesh(self):
        group = {
            self.admin.mesh_user_id: {"rights": 4088024},
            self.tech.mesh_user_id: {"rights": 4088024},
        }
        ms = self._run(
            node_links={
                self.node1: {self.limited.mesh_user_id: {"rights": 4088024}},
                self.node2: {},
            },
            group_links=group,
            mesh_users={},
        )
        ms.delete_user_from_mesh.assert_not_called()
        ms.add_users_to_mesh_group.assert_not_called()
        ms.remove_user_from_mesh_group.assert_not_called()
        ms.add_users_to_node.assert_not_called()
        ms.delete_users_from_node.assert_not_called()

    @override_settings(TRMM_MESH_SYNC_LEGACY_LINK_CLEANUP_PER_RUN=1)
    def test_legacy_device_links_removed_throttled_and_only_after_group_link(self):
        legacy = {
            self.admin.mesh_user_id: {"rights": 4088024},
            self.tech.mesh_user_id: {"rights": 4088024},
        }
        node1_links = {**legacy, self.limited.mesh_user_id: {"rights": 4088024}}

        # no group link yet: legacy device links must stay (no loss of access)
        ms = self._run(
            node_links={self.node1: node1_links, self.node2: dict(legacy)},
            group_links={},
            mesh_users={},
        )
        ms.delete_users_from_node.assert_not_called()

        # with the group link: legacy links are removed, one device per run here
        ms = self._run(
            node_links={self.node1: node1_links, self.node2: dict(legacy)},
            group_links=dict(legacy),
            mesh_users={},
        )
        removed = self._calls(ms, "delete_users_from_node")
        self.assertEqual(len(removed), 1)
        self.assertEqual(
            set(removed[0]["user_ids"]),
            {self.admin.mesh_user_id, self.tech.mesh_user_id},
        )

    def test_user_restricted_later_loses_group_link(self):
        self.tech.role.can_view_sites.set([self.other_site])
        group = {
            self.admin.mesh_user_id: {"rights": 4088024},
            self.tech.mesh_user_id: {"rights": 4088024},
        }
        ms = self._run(
            node_links={
                self.node1: {self.limited.mesh_user_id: {"rights": 4088024}},
                self.node2: {},
            },
            group_links=group,
            mesh_users={},
        )
        ms.remove_user_from_mesh_group.assert_called_once_with(
            mesh_id=MESH_ID, user_id=self.tech.mesh_user_id
        )
        self.assertIn(
            {"node_id": self.node2, "user_ids": [self.tech.mesh_user_id]},
            self._calls(ms, "add_users_to_node"),
        )

    def test_user_without_mesh_perms_is_deleted(self):
        group = {
            self.admin.mesh_user_id: {"rights": 4088024},
            self.tech.mesh_user_id: {"rights": 4088024},
            self.nomesh.mesh_user_id: {"rights": 4088024},
        }
        ms = self._run(
            node_links={
                self.node1: {self.limited.mesh_user_id: {"rights": 4088024}},
                self.node2: {},
            },
            group_links=group,
            mesh_users={},
        )
        ms.delete_user_from_mesh.assert_called_once_with(
            mesh_user_id=self.nomesh.mesh_user_id
        )
        # deleting the user already removes its group link
        ms.remove_user_from_mesh_group.assert_not_called()
