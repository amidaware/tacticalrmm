from unittest.mock import patch

from django.test import override_settings
from model_bakery import baker, seq

from accounts.models import APIKey, User
from accounts.serializers import APIKeySerializer
from tacticalrmm.constants import AgentDblClick, AgentTableTabs, ClientTreeSort
from tacticalrmm.test import TacticalTestCase


class TestAccounts(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.setup_client()
        self.bob = User(username="bob")
        self.bob.set_password("hunter2")
        self.bob.save()

    def test_check_creds(self):
        url = "/v2/checkcreds/"

        data = {"username": "bob", "password": "hunter2"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("totp", r.data.keys())
        self.assertEqual(r.data["totp"], False)

        data = {"username": "bob", "password": "a3asdsa2314"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, "Bad credentials")

        data = {"username": "billy", "password": "hunter2"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, "Bad credentials")

        self.bob.totp_key = "AB5RI6YPFTZAS52G"
        self.bob.save()
        data = {"username": "bob", "password": "hunter2"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["totp"], True)

        # test user set to block dashboard logins
        self.bob.block_dashboard_login = True
        self.bob.save()
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

    @patch("pyotp.TOTP.verify")
    def test_login_view(self, mock_verify):
        url = "/v2/login/"

        mock_verify.return_value = True
        data = {"username": "bob", "password": "hunter2", "twofactor": "123456"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("expiry", r.data.keys())
        self.assertIn("token", r.data.keys())

        mock_verify.return_value = False
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, "Bad credentials")

        mock_verify.return_value = True
        data = {"username": "bob", "password": "asd234234asd", "twofactor": "123456"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("non_field_errors", r.data.keys())

    # @override_settings(DEBUG=True)
    # @patch("pyotp.TOTP.verify")
    # def test_debug_login_view(self, mock_verify):
    #     url = "/login/"
    #     mock_verify.return_value = True

    #     data = {"username": "bob", "password": "hunter2", "twofactor": "sekret"}
    #     r = self.client.post(url, data, format="json")
    #     self.assertEqual(r.status_code, 200)
    #     self.assertIn("expiry", r.data.keys())
    #     self.assertIn("token", r.data.keys())


class TestGetAddUsers(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_get(self):
        url = "/accounts/users/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        assert any(i["username"] == "john" for i in r.json())

        assert not any(
            i["username"] == "71AHC-AA813-HH1BC-AAHH5-00013|DESKTOP-TEST123"
            for i in r.json()
        )

        self.check_not_authenticated("get", url)

    def test_post_add_duplicate(self):
        url = "/accounts/users/"
        data = {
            "username": "john",
            "password": "askdjaskdj",
            "email": "john@example.com",
            "first_name": "",
            "last_name": "",
        }
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

    def test_post_add_new(self):
        url = "/accounts/users/"
        data = {
            "username": "jane",
            "password": "ASd1234asd",
            "email": "jane@example.com",
            "first_name": "",
            "last_name": "",
        }
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, "jane")

        self.check_not_authenticated("post", url)


class GetUpdateDeleteUser(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_get(self):
        url = f"/accounts/{self.john.pk}/users/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["username"], "john")

        url = "/accounts/2345/users/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("get", url)

    def test_put(self):
        url = f"/accounts/{self.john.pk}/users/"
        data = {
            "id": self.john.pk,
            "username": "john",
            "email": "johndoe@xlawgaming.com",
            "first_name": "John",
            "last_name": "Doe",
        }
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        data["email"] = "aksjdaksjdklasjdlaksdj"
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("put", url)

    @override_settings(ROOT_USER="john")
    def test_put_root_user(self):
        url = f"/accounts/{self.john.pk}/users/"
        data = {
            "id": self.john.pk,
            "username": "john",
            "email": "johndoe@xlawgaming.com",
            "first_name": "John",
            "last_name": "Doe",
        }
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)

    @override_settings(ROOT_USER="john")
    def test_put_not_root_user(self):
        url = f"/accounts/{self.john.pk}/users/"
        data = {
            "id": self.john.pk,
            "username": "john",
            "email": "johndoe@xlawgaming.com",
            "first_name": "John",
            "last_name": "Doe",
        }
        self.client.force_authenticate(user=self.alice)
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 400)

    def test_delete(self):
        url = f"/accounts/{self.john.pk}/users/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 200)

        url = "/accounts/893452/users/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("delete", url)

    @override_settings(ROOT_USER="john")
    def test_delete_root_user(self):
        url = f"/accounts/{self.john.pk}/users/"
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 200)

    @override_settings(ROOT_USER="john")
    def test_delete_non_root_user(self):
        url = f"/accounts/{self.john.pk}/users/"
        self.client.force_authenticate(user=self.alice)
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 400)


class TestUserAction(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_post(self):
        url = "/accounts/users/reset/"
        data = {"id": self.john.pk, "password": "3ASDjh2345kJA!@#)#@__123"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        data["id"] = 43924
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("post", url)

    @override_settings(ROOT_USER="john")
    def test_post_root_user(self):
        url = "/accounts/users/reset/"
        data = {"id": self.john.pk, "password": "3ASDjh2345kJA!@#)#@__123"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

    @override_settings(ROOT_USER="john")
    def test_post_non_root_user(self):
        url = "/accounts/users/reset/"
        data = {"id": self.john.pk, "password": "3ASDjh2345kJA!@#)#@__123"}
        self.client.force_authenticate(user=self.alice)
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

    def test_put(self):
        url = "/accounts/users/reset/"
        data = {"id": self.john.pk}
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        user = User.objects.get(pk=self.john.pk)
        self.assertEqual(user.totp_key, "")

        self.check_not_authenticated("put", url)

    @override_settings(ROOT_USER="john")
    def test_put_root_user(self):
        url = "/accounts/users/reset/"
        data = {"id": self.john.pk}
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        user = User.objects.get(pk=self.john.pk)
        self.assertEqual(user.totp_key, "")

    @override_settings(ROOT_USER="john")
    def test_put_non_root_user(self):
        url = "/accounts/users/reset/"
        data = {"id": self.john.pk}
        self.client.force_authenticate(user=self.alice)
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 400)

    def test_user_ui(self):
        url = "/accounts/users/ui/"

        data = {
            "dark_mode": True,
            "show_community_scripts": True,
            "agent_dblclick_action": AgentDblClick.EDIT_AGENT,
            "default_agent_tbl_tab": AgentTableTabs.MIXED,
            "client_tree_sort": ClientTreeSort.ALPHA,
            "client_tree_splitter": 14,
            "loading_bar_color": "green",
            "clear_search_when_switching": False,
        }
        r = self.client.patch(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("patch", url)


class TestUserReset(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_reset_pw(self):
        url = "/accounts/resetpw/"
        data = {"password": "superSekret123456"}
        r = self.client.put(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("put", url)

    def test_reset_2fa(self):
        url = "/accounts/reset2fa/"
        r = self.client.put(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("put", url)


class TestAPIKeyViews(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.authenticate()

    def test_get_api_keys(self):
        url = "/accounts/apikeys/"
        apikeys = baker.make("accounts.APIKey", key=seq("APIKEY"), _quantity=3)

        serializer = APIKeySerializer(apikeys, many=True)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(serializer.data, resp.data)

        self.check_not_authenticated("get", url)

    def test_add_api_keys(self):
        url = "/accounts/apikeys/"

        user = baker.make("accounts.User")
        data = {"name": "Name", "user": user.id, "expiration": None}

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(APIKey.objects.filter(name="Name").exists())
        self.assertTrue(APIKey.objects.get(name="Name").key)

        self.check_not_authenticated("post", url)

    def test_modify_api_key(self):
        # test a call where api key doesn't exist
        resp = self.client.put("/accounts/apikeys/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        apikey = baker.make("accounts.APIKey", name="Test")
        url = f"/accounts/apikeys/{apikey.pk}/"

        data = {"name": "New Name"}

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        apikey = APIKey.objects.get(pk=apikey.pk)
        self.assertEqual(apikey.name, "New Name")

        self.check_not_authenticated("put", url)

    def test_delete_api_key(self):
        # test a call where api key doesn't exist
        resp = self.client.delete("/accounts/apikeys/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        # test delete api key
        apikey = baker.make("accounts.APIKey")
        url = f"/accounts/apikeys/{apikey.pk}/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        self.assertFalse(APIKey.objects.filter(pk=apikey.pk).exists())

        self.check_not_authenticated("delete", url)


class TestTOTPSetup(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_post(self):
        url = "/accounts/users/setup_totp/"
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn("username", r.json().keys())
        self.assertIn("totp_key", r.json().keys())
        self.assertIn("qr_url", r.json().keys())
        self.assertEqual("john", r.json()["username"])
        self.assertIn("otpauth://totp", r.json()["qr_url"])

        self.check_not_authenticated("post", url)

    def test_post_totp_set(self):
        url = "/accounts/users/setup_totp/"
        self.john.totp_key = "AB5RI6YPFTZAS52G"
        self.john.save()

        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, False)


class TestAPIAuthentication(TacticalTestCase):
    def setUp(self):
        # create User and associate to API Key
        self.user = User.objects.create(username="api_user", is_superuser=True)
        self.api_key = APIKey.objects.create(
            name="Test Token", key="123456", user=self.user
        )

        self.setup_client()

    def test_api_auth(self):
        url = "/clients/"
        # auth should fail if no header set
        self.check_not_authenticated("get", url)

        # invalid api key in header should return code 400
        self.client.credentials(HTTP_X_API_KEY="000000")
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 401)

        # valid api key in header should return code 200
        self.client.credentials(HTTP_X_API_KEY="123456")
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)
