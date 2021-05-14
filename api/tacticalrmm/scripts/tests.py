import json
import os
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from model_bakery import baker

from tacticalrmm.test import TacticalTestCase

from .models import Script
from .serializers import ScriptSerializer, ScriptTableSerializer


class TestScriptViews(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.authenticate()

    def test_get_scripts(self):
        url = "/scripts/scripts/"
        scripts = baker.make("scripts.Script", _quantity=3)

        serializer = ScriptTableSerializer(scripts, many=True)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(serializer.data, resp.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_add_script(self):
        url = f"/scripts/scripts/"

        data = {
            "name": "Name",
            "description": "Description",
            "shell": "powershell",
            "category": "New",
            "code": "Some Test Code\nnew Line",
            "default_timeout": 99,
            "args": ["hello", "world", r"{{agent.public_ip}}"],
            "favorite": False,
        }

        # test without file upload
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Script.objects.filter(name="Name").exists())
        self.assertEqual(Script.objects.get(name="Name").code, data["code"])

        # test with file upload
        # file with 'Test' as content
        file = SimpleUploadedFile(
            "test_script.bat", b"\x54\x65\x73\x74", content_type="text/plain"
        )
        data = {
            "name": "New Name",
            "description": "Description",
            "shell": "cmd",
            "category": "New",
            "filename": file,
            "default_timeout": 4455,
            "args": json.dumps(
                ["hello", "world", r"{{agent.public_ip}}"]
            ),  # simulate javascript's JSON.stringify() for formData
        }

        # test with file upload
        resp = self.client.post(url, data, format="multipart")
        self.assertEqual(resp.status_code, 200)
        script = Script.objects.filter(name="New Name").first()
        self.assertEquals(script.code, "Test")

        self.check_not_authenticated("post", url)

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
            "code": "Test Code\nAnother Line",
            "default_timeout": 13344556,
        }

        # test edit a userdefined script
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        script = Script.objects.get(pk=script.pk)
        self.assertEquals(script.description, "Description Change")
        self.assertEquals(script.code, "Test Code\nAnother Line")

        # test edit a builtin script

        data = {"name": "New Name", "description": "New Desc", "code": "Some New Code"}
        builtin_script = baker.make_recipe("scripts.script", script_type="builtin")

        resp = self.client.put(
            f"/scripts/{builtin_script.pk}/script/", data, format="json"
        )
        self.assertEqual(resp.status_code, 400)

        data = {
            "name": script.name,
            "description": "Description Change",
            "shell": script.shell,
            "favorite": True,
            "code": "Test Code\nAnother Line",
            "default_timeout": 54345,
        }
        # test marking a builtin script as favorite
        resp = self.client.put(
            f"/scripts/{builtin_script.pk}/script/", data, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Script.objects.get(pk=builtin_script.pk).favorite)

        self.check_not_authenticated("put", url)

    def test_get_script(self):
        # test a call where script doesn't exist
        resp = self.client.get("/scripts/500/script/", format="json")
        self.assertEqual(resp.status_code, 404)

        script = baker.make("scripts.Script")
        url = f"/scripts/{script.pk}/script/"  # type: ignore
        serializer = ScriptSerializer(script)
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(serializer.data, resp.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_delete_script(self):
        # test a call where script doesn't exist
        resp = self.client.delete("/scripts/500/script/", format="json")
        self.assertEqual(resp.status_code, 404)

        # test delete script
        script = baker.make_recipe("scripts.script")
        url = f"/scripts/{script.pk}/script/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        self.assertFalse(Script.objects.filter(pk=script.pk).exists())

        # test delete community script
        script = baker.make_recipe("scripts.script", script_type="builtin")
        url = f"/scripts/{script.pk}/script/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("delete", url)

    def test_download_script(self):
        # test a call where script doesn't exist
        resp = self.client.get("/scripts/500/download/", format="json")
        self.assertEqual(resp.status_code, 404)

        # return script code property should be "Test"

        # test powershell file
        script = baker.make(
            "scripts.Script", code_base64="VGVzdA==", shell="powershell"
        )
        url = f"/scripts/{script.pk}/download/"  # type: ignore

        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {"filename": f"{script.name}.ps1", "code": "Test"})  # type: ignore

        # test batch file
        script = baker.make("scripts.Script", code_base64="VGVzdA==", shell="cmd")
        url = f"/scripts/{script.pk}/download/"  # type: ignore

        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {"filename": f"{script.name}.bat", "code": "Test"})  # type: ignore

        # test python file
        script = baker.make("scripts.Script", code_base64="VGVzdA==", shell="python")
        url = f"/scripts/{script.pk}/download/"  # type: ignore

        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {"filename": f"{script.name}.py", "code": "Test"})  # type: ignore

        self.check_not_authenticated("get", url)

    def test_community_script_json_file(self):
        valid_shells = ["powershell", "python", "cmd"]

        if not settings.DOCKER_BUILD:
            scripts_dir = os.path.join(Path(settings.BASE_DIR).parents[1], "scripts")
        else:
            scripts_dir = settings.SCRIPTS_DIR

        with open(
            os.path.join(settings.BASE_DIR, "scripts/community_scripts.json")
        ) as f:
            info = json.load(f)

        guids = []
        for script in info:
            fn: str = script["filename"]
            self.assertTrue(os.path.exists(os.path.join(scripts_dir, fn)))
            self.assertTrue(script["filename"])
            self.assertTrue(script["name"])
            self.assertTrue(script["description"])
            self.assertTrue(script["shell"])
            self.assertIn(script["shell"], valid_shells)

            if fn.endswith(".ps1"):
                self.assertEqual(script["shell"], "powershell")
            elif fn.endswith(".bat"):
                self.assertEqual(script["shell"], "cmd")
            elif fn.endswith(".py"):
                self.assertEqual(script["shell"], "python")

            if "args" in script.keys():
                self.assertIsInstance(script["args"], list)

            # allows strings as long as they can be type casted to int
            if "default_timeout" in script.keys():
                self.assertIsInstance(int(script["default_timeout"]), int)

            self.assertIn("guid", script.keys())
            guids.append(script["guid"])

        # check guids are unique
        self.assertEqual(len(guids), len(set(guids)))

    def test_load_community_scripts(self):
        with open(
            os.path.join(settings.BASE_DIR, "scripts/community_scripts.json")
        ) as f:
            info = json.load(f)

        Script.load_community_scripts()

        community_scripts_count = Script.objects.filter(script_type="builtin").count()
        if len(info) != community_scripts_count:
            raise Exception(
                f"There are {len(info)} scripts in json file but only {community_scripts_count} in database"
            )

        # test updating already added community scripts
        Script.load_community_scripts()
        community_scripts_count2 = Script.objects.filter(script_type="builtin").count()
        self.assertEqual(len(info), community_scripts_count2)

    def test_community_script_has_jsonfile_entry(self):
        with open(
            os.path.join(settings.BASE_DIR, "scripts/community_scripts.json")
        ) as f:
            info = json.load(f)

        filenames = [i["filename"] for i in info]

        # normal
        if not settings.DOCKER_BUILD:
            scripts_dir = os.path.join(Path(settings.BASE_DIR).parents[1], "scripts")
        # docker
        else:
            scripts_dir = settings.SCRIPTS_DIR

        with os.scandir(scripts_dir) as it:
            for f in it:
                if not f.name.startswith(".") and f.is_file():
                    if f.name not in filenames:
                        raise Exception(
                            f"{f.name} is missing an entry in community_scripts.json"
                        )

    def test_script_filenames_do_not_contain_spaces(self):
        with open(
            os.path.join(settings.BASE_DIR, "scripts/community_scripts.json")
        ) as f:
            info = json.load(f)
            for script in info:
                fn: str = script["filename"]
                if " " in fn:
                    raise Exception(f"{fn} must not contain spaces in filename")

    def test_script_arg_variable_replacement(self):

        agent = baker.make_recipe("agents.agent", public_ip="12.12.12.12")
        args = [
            "-Parameter",
            "-Another {{agent.public_ip}}",
            "-Client {{client.name}}",
            "-Site {{site.name}}",
        ]

        self.assertEqual(
            [
                "-Parameter",
                "-Another '12.12.12.12'",
                f"-Client '{agent.client.name}'",
                f"-Site '{agent.site.name}'",
            ],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

    def test_script_arg_replacement_custom_field(self):
        agent = baker.make_recipe("agents.agent")
        field = baker.make(
            "core.CustomField",
            name="Test Field",
            model="agent",
            type="text",
            default_value_string="DEFAULT",
        )

        args = ["-Parameter", "-Another {{agent.Test Field}}"]

        # test default value
        self.assertEqual(
            ["-Parameter", "-Another 'DEFAULT'"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

        # test with set value
        baker.make(
            "agents.AgentCustomField",
            field=field,
            agent=agent,
            string_value="CUSTOM VALUE",
        )
        self.assertEqual(
            ["-Parameter", "-Another 'CUSTOM VALUE'"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

    def test_script_arg_replacement_client_custom_fields(self):
        agent = baker.make_recipe("agents.agent")
        field = baker.make(
            "core.CustomField",
            name="Test Field",
            model="client",
            type="text",
            default_value_string="DEFAULT",
        )

        args = ["-Parameter", "-Another {{client.Test Field}}"]

        # test default value
        self.assertEqual(
            ["-Parameter", "-Another 'DEFAULT'"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

        # test with set value
        baker.make(
            "clients.ClientCustomField",
            field=field,
            client=agent.client,
            string_value="CUSTOM VALUE",
        )
        self.assertEqual(
            ["-Parameter", "-Another 'CUSTOM VALUE'"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

    def test_script_arg_replacement_site_custom_fields(self):
        agent = baker.make_recipe("agents.agent")
        field = baker.make(
            "core.CustomField",
            name="Test Field",
            model="site",
            type="text",
            default_value_string="DEFAULT",
        )

        args = ["-Parameter", "-Another {{site.Test Field}}"]

        # test default value
        self.assertEqual(
            ["-Parameter", "-Another 'DEFAULT'"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

        # test with set value
        value = baker.make(
            "clients.SiteCustomField",
            field=field,
            site=agent.site,
            string_value="CUSTOM VALUE",
        )
        self.assertEqual(
            ["-Parameter", "-Another 'CUSTOM VALUE'"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

        # test with set but empty field value
        value.string_value = ""  # type: ignore
        value.save()  # type: ignore

        self.assertEqual(
            ["-Parameter", "-Another 'DEFAULT'"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

        # test blank default and value
        field.default_value_string = ""  # type: ignore
        field.save()  # type: ignore

        self.assertEqual(
            ["-Parameter", "-Another ''"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

    def test_script_arg_replacement_array_fields(self):
        agent = baker.make_recipe("agents.agent")
        field = baker.make(
            "core.CustomField",
            name="Test Field",
            model="agent",
            type="multiple",
            default_values_multiple=["this", "is", "an", "array"],
        )

        args = ["-Parameter", "-Another {{agent.Test Field}}"]

        # test default value
        self.assertEqual(
            ["-Parameter", "-Another 'this,is,an,array'"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

        # test with set value and python shell
        baker.make(
            "agents.AgentCustomField",
            field=field,
            agent=agent,
            multiple_value=["this", "is", "new"],
        )
        self.assertEqual(
            ["-Parameter", "-Another 'this,is,new'"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

    def test_script_arg_replacement_boolean_fields(self):
        agent = baker.make_recipe("agents.agent")
        field = baker.make(
            "core.CustomField",
            name="Test Field",
            model="agent",
            type="checkbox",
            default_value_bool=True,
        )

        args = ["-Parameter", "-Another {{agent.Test Field}}"]

        # test default value with python
        self.assertEqual(
            ["-Parameter", "-Another 1"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

        # test with set value and python shell
        custom = baker.make(
            "agents.AgentCustomField",
            field=field,
            agent=agent,
            bool_value=False,
        )
        self.assertEqual(
            ["-Parameter", "-Another 0"],
            Script.parse_script_args(agent=agent, shell="python", args=args),
        )

        # test with set value and cmd shell
        self.assertEqual(
            ["-Parameter", "-Another 0"],
            Script.parse_script_args(agent=agent, shell="cmd", args=args),
        )

        # test with set value and powershell
        self.assertEqual(
            ["-Parameter", "-Another $False"],
            Script.parse_script_args(agent=agent, shell="powershell", args=args),
        )

        # test with True value powershell
        custom.bool_value = True  # type: ignore
        custom.save()  # type: ignore

        self.assertEqual(
            ["-Parameter", "-Another $True"],
            Script.parse_script_args(agent=agent, shell="powershell", args=args),
        )
