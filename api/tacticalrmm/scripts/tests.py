import json
import os
from pathlib import Path
from django.conf import settings
from tacticalrmm.test import TacticalTestCase
from model_bakery import baker
from .serializers import ScriptSerializer
from .models import Script


class TestScriptViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()

    def test_get_scripts(self):
        url = "/scripts/scripts/"
        scripts = baker.make("scripts.Script", _quantity=3)

        serializer = ScriptSerializer(scripts, many=True)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(serializer.data, resp.data)

        self.check_not_authenticated("get", url)

    # TODO Need to test file uploads and saves
    def test_add_script(self):
        pass

    def test_modify_script(self):
        # test a call where script doesn't exist
        resp = self.client.put("/scripts/500/script/", format="json")
        self.assertEqual(resp.status_code, 404)

        # make a userdefined script
        script = baker.make_recipe("scripts.script")
        url = f"/scripts/{script.pk}/script/"

        data = {
            "name": script.name,
            "description": "Description Change",
            "shell": script.shell,
        }

        # test edit a userdefined script
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEquals(
            Script.objects.get(pk=script.pk).description, "Description Change"
        )

        # test edit a builtin script
        builtin_script = baker.make_recipe("scripts.builtin_script")
        resp = self.client.put(
            f"/scripts/{builtin_script.pk}/script/", data, format="json"
        )
        self.assertEqual(resp.status_code, 400)

        # TODO Test changing script file

        self.check_not_authenticated("put", url)

    def test_get_script(self):
        # test a call where script doesn't exist
        resp = self.client.get("/scripts/500/script/", format="json")
        self.assertEqual(resp.status_code, 404)

        script = baker.make("scripts.Script")
        url = f"/scripts/{script.pk}/script/"
        serializer = ScriptSerializer(script)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(serializer.data, resp.data)

        self.check_not_authenticated("get", url)

    def test_delete_script(self):
        # test a call where script doesn't exist
        resp = self.client.delete("/scripts/500/script/", format="json")
        self.assertEqual(resp.status_code, 404)

        script = baker.make_recipe("scripts.script")
        url = f"/scripts/{script.pk}/script/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        self.assertFalse(Script.objects.filter(pk=script.pk).exists())

        self.check_not_authenticated("delete", url)

    # TODO Need to mock file open
    def test_download_script(self):
        pass

    def test_load_community_scripts(self):
        valid_shells = ["powershell", "python", "cmd"]
        scripts_dir = os.path.join(Path(settings.BASE_DIR).parents[1], "scripts")

        with open(
            os.path.join(settings.BASE_DIR, "scripts/community_scripts.json")
        ) as f:
            info = json.load(f)

        for script in info:
            self.assertTrue(
                os.path.exists(os.path.join(scripts_dir, script["filename"]))
            )
            self.assertTrue(script["filename"])
            self.assertTrue(script["name"])
            self.assertTrue(script["description"])
            self.assertTrue(script["shell"])
            self.assertTrue(script["description"])
            self.assertIn(script["shell"], valid_shells)
