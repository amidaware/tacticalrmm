from django.utils import timezone as djangotime
from model_bakery import baker

from autotasks.models import TaskResult
from tacticalrmm.constants import CustomFieldModel, CustomFieldType, TaskStatus
from tacticalrmm.test import TacticalTestCase


class TestAPIv3(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()
        self.agent = baker.make_recipe("agents.agent")

    def test_get_checks(self):
        agent = baker.make_recipe("agents.agent")
        url = f"/api/v3/{agent.agent_id}/checkrunner/"

        # add a check
        check1 = baker.make_recipe("checks.ping_check", agent=agent)
        check_result1 = baker.make(
            "checks.CheckResult", agent=agent, assigned_check=check1
        )
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["check_interval"], self.agent.check_interval)
        self.assertEqual(len(r.data["checks"]), 1)

        # override check run interval
        check2 = baker.make_recipe(
            "checks.diskspace_check", agent=agent, run_interval=20
        )
        check_result2 = baker.make(
            "checks.CheckResult", agent=agent, assigned_check=check2
        )

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["checks"]), 2)
        self.assertEqual(r.data["check_interval"], 20)

        # Set last_run on both checks and should return an empty list
        check_result1.last_run = djangotime.now()
        check_result1.save()
        check_result2.last_run = djangotime.now()
        check_result2.save()

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["check_interval"], 20)
        self.assertFalse(r.data["checks"])

        # set last_run greater than interval
        check_result1.last_run = djangotime.now() - djangotime.timedelta(seconds=200)
        check_result1.save()
        check_result2.last_run = djangotime.now() - djangotime.timedelta(seconds=200)
        check_result2.save()

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["check_interval"], 20)
        self.assertEqual(len(r.data["checks"]), 2)

        url = "/api/v3/Maj34ACb324j234asdj2n34kASDjh34-DESKTOPTEST123/checkrunner/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("get", url)

    def test_checkrunner_interval(self):
        url = f"/api/v3/{self.agent.agent_id}/checkinterval/"
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {"agent": self.agent.pk, "check_interval": self.agent.check_interval},
        )

        # add check to agent with check interval set
        baker.make_recipe("checks.ping_check", agent=self.agent, run_interval=30)

        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {"agent": self.agent.pk, "check_interval": 30},
        )

        # minimum check run interval is 15 seconds
        baker.make_recipe("checks.ping_check", agent=self.agent, run_interval=5)

        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {"agent": self.agent.pk, "check_interval": 15},
        )

    def test_run_checks(self):
        # force run all checks regardless of interval
        agent = baker.make_recipe("agents.online_agent")
        baker.make_recipe("checks.ping_check", agent=agent)
        baker.make_recipe("checks.diskspace_check", agent=agent)
        baker.make_recipe("checks.cpuload_check", agent=agent)
        baker.make_recipe("checks.memory_check", agent=agent)
        baker.make_recipe("checks.eventlog_check", agent=agent)
        for _ in range(10):
            baker.make_recipe("checks.script_check", agent=agent)

        url = f"/api/v3/{agent.agent_id}/runchecks/"
        r = self.client.get(url)
        self.assertEqual(r.json()["agent"], agent.pk)
        self.assertIsInstance(r.json()["check_interval"], int)
        self.assertEqual(len(r.json()["checks"]), 15)

    def test_task_runner_get(self):
        r = self.client.get("/api/v3/500/asdf9df9dfdf/taskrunner/")
        self.assertEqual(r.status_code, 404)

        script = baker.make("scripts.script")

        # setup data
        task_actions = [
            {"type": "cmd", "command": "whoami", "timeout": 10, "shell": "cmd"},
            {
                "type": "script",
                "script": script.id,
                "script_args": ["test"],
                "timeout": 30,
                "env_vars": ["hello=world", "foo=bar"],
            },
            {
                "type": "script",
                "script": 3,
                "script_args": [],
                "timeout": 30,
                "env_vars": ["hello=world", "foo=bar"],
            },
        ]

        agent = baker.make_recipe("agents.agent")
        task = baker.make("autotasks.AutomatedTask", agent=agent, actions=task_actions)

        url = f"/api/v3/{task.pk}/{agent.agent_id}/taskrunner/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_task_runner_results(self):
        from agents.models import AgentCustomField

        r = self.client.patch("/api/v3/500/asdf9df9dfdf/taskrunner/")
        self.assertEqual(r.status_code, 404)

        # setup data
        agent = baker.make_recipe("agents.agent")
        task = baker.make("autotasks.AutomatedTask", agent=agent)
        task_result = baker.make("autotasks.TaskResult", agent=agent, task=task)

        url = f"/api/v3/{task.pk}/{agent.agent_id}/taskrunner/"

        # test passing task
        data = {
            "stdout": "test test \ntestest stdgsd\n",
            "stderr": "",
            "retcode": 0,
            "execution_time": 3.560,
        }

        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            TaskResult.objects.get(pk=task_result.pk).status == TaskStatus.PASSING
        )

        # test failing task
        data = {
            "stdout": "test test \ntestest stdgsd\n",
            "stderr": "",
            "retcode": 1,
            "execution_time": 3.560,
        }

        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            TaskResult.objects.get(pk=task_result.pk).status == TaskStatus.FAILING
        )

        # test collector task
        text = baker.make(
            "core.CustomField",
            model=CustomFieldModel.AGENT,
            type=CustomFieldType.TEXT,
            name="Test",
        )
        boolean = baker.make(
            "core.CustomField",
            model=CustomFieldModel.AGENT,
            type=CustomFieldType.CHECKBOX,
            name="Test1",
        )
        multiple = baker.make(
            "core.CustomField",
            model=CustomFieldModel.AGENT,
            type=CustomFieldType.MULTIPLE,
            name="Test2",
        )

        # test text fields
        task.custom_field = text
        task.save()

        # test failing failing with stderr
        data = {
            "stdout": "test test \nthe last line",
            "stderr": "This is an error",
            "retcode": 1,
            "execution_time": 3.560,
        }

        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            TaskResult.objects.get(pk=task_result.pk).status == TaskStatus.FAILING
        )

        # test saving to text field
        data = {
            "stdout": "test test \nthe last line",
            "stderr": "",
            "retcode": 0,
            "execution_time": 3.560,
        }

        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            TaskResult.objects.get(pk=task_result.pk).status, TaskStatus.PASSING
        )
        self.assertEqual(
            AgentCustomField.objects.get(field=text, agent=task.agent).value,
            "the last line",
        )

        # test saving to checkbox field
        task.custom_field = boolean
        task.save()

        data = {
            "stdout": "1",
            "stderr": "",
            "retcode": 0,
            "execution_time": 3.560,
        }

        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            TaskResult.objects.get(pk=task_result.pk).status, TaskStatus.PASSING
        )
        self.assertTrue(
            AgentCustomField.objects.get(field=boolean, agent=task.agent).value
        )

        # test saving to multiple field with commas
        task.custom_field = multiple
        task.save()

        data = {
            "stdout": "this,is,an,array",
            "stderr": "",
            "retcode": 0,
            "execution_time": 3.560,
        }

        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            TaskResult.objects.get(pk=task_result.pk).status, TaskStatus.PASSING
        )
        self.assertEqual(
            AgentCustomField.objects.get(field=multiple, agent=task.agent).value,
            ["this", "is", "an", "array"],
        )

        # test mutiple with a single value
        data = {
            "stdout": "this",
            "stderr": "",
            "retcode": 0,
            "execution_time": 3.560,
        }

        r = self.client.patch(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            TaskResult.objects.get(pk=task_result.pk).status, TaskStatus.PASSING
        )
        self.assertEqual(
            AgentCustomField.objects.get(field=multiple, agent=task.agent).value,
            ["this"],
        )

    def test_get_agent_config(self):
        agent = baker.make_recipe("agents.online_agent")
        url = f"/api/v3/{agent.agent_id}/config/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
