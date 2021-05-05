import datetime as dt
from unittest.mock import call, patch

from django.utils import timezone as djangotime
from model_bakery import baker

from tacticalrmm.test import TacticalTestCase

from .models import AutomatedTask
from .serializers import AutoTaskSerializer
from .tasks import create_win_task_schedule, remove_orphaned_win_tasks, run_win_task


class TestAutotaskViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("automation.tasks.generate_agent_autotasks_task.delay")
    @patch("autotasks.tasks.create_win_task_schedule.delay")
    def test_add_autotask(
        self, create_win_task_schedule, generate_agent_autotasks_task
    ):
        url = "/tasks/automatedtasks/"

        # setup data
        script = baker.make_recipe("scripts.script")
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        check = baker.make_recipe("checks.diskspace_check", agent=agent)

        # test script set to invalid pk
        data = {"autotask": {"script": 500}}

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 404)

        # test invalid policy
        data = {"autotask": {"script": script.id}, "policy": 500}

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 404)

        # test invalid agent
        data = {
            "autotask": {"script": script.id},
            "agent": 500,
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 404)

        # test add task to agent
        data = {
            "autotask": {
                "name": "Test Task Scheduled with Assigned Check",
                "run_time_days": ["Sunday", "Monday", "Friday"],
                "run_time_minute": "10:00",
                "timeout": 120,
                "enabled": True,
                "script": script.id,
                "script_args": None,
                "task_type": "scheduled",
                "assigned_check": check.id,
            },
            "agent": agent.id,
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        create_win_task_schedule.assert_called()

        # test add task to policy
        data = {
            "autotask": {
                "name": "Test Task Manual",
                "run_time_days": [],
                "timeout": 120,
                "enabled": True,
                "script": script.id,
                "script_args": None,
                "task_type": "manual",
                "assigned_check": None,
            },
            "policy": policy.id,  # type: ignore
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        generate_agent_autotasks_task.assert_called_with(policy=policy.id)  # type: ignore

        self.check_not_authenticated("post", url)

    def test_get_autotask(self):

        # setup data
        agent = baker.make_recipe("agents.agent")
        baker.make("autotasks.AutomatedTask", agent=agent, _quantity=3)

        url = f"/tasks/{agent.id}/automatedtasks/"

        resp = self.client.get(url, format="json")
        serializer = AutoTaskSerializer(agent)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    @patch("autotasks.tasks.enable_or_disable_win_task.delay")
    @patch("automation.tasks.update_policy_autotasks_fields_task.delay")
    def test_update_autotask(
        self, update_policy_autotasks_fields_task, enable_or_disable_win_task
    ):
        # setup data
        agent = baker.make_recipe("agents.agent")
        agent_task = baker.make("autotasks.AutomatedTask", agent=agent)
        policy = baker.make("automation.Policy")
        policy_task = baker.make("autotasks.AutomatedTask", policy=policy)

        # test invalid url
        resp = self.client.patch("/tasks/500/automatedtasks/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"/tasks/{agent_task.id}/automatedtasks/"  # type: ignore

        # test editing agent task
        data = {"enableordisable": False}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        enable_or_disable_win_task.assert_called_with(pk=agent_task.id)  # type: ignore

        url = f"/tasks/{policy_task.id}/automatedtasks/"  # type: ignore

        # test editing policy task
        data = {"enableordisable": True}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        update_policy_autotasks_fields_task.assert_called_with(
            task=policy_task.id, update_agent=True  # type: ignore
        )

        self.check_not_authenticated("patch", url)

    @patch("autotasks.tasks.delete_win_task_schedule.delay")
    @patch("automation.tasks.delete_policy_autotasks_task.delay")
    def test_delete_autotask(
        self, delete_policy_autotasks_task, delete_win_task_schedule
    ):
        # setup data
        agent = baker.make_recipe("agents.agent")
        agent_task = baker.make("autotasks.AutomatedTask", agent=agent)
        policy = baker.make("automation.Policy")
        policy_task = baker.make("autotasks.AutomatedTask", policy=policy)

        # test invalid url
        resp = self.client.delete("/tasks/500/automatedtasks/", format="json")
        self.assertEqual(resp.status_code, 404)

        # test delete agent task
        url = f"/tasks/{agent_task.id}/automatedtasks/"  # type: ignore
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)
        delete_win_task_schedule.assert_called_with(pk=agent_task.id)  # type: ignore

        # test delete policy task
        url = f"/tasks/{policy_task.id}/automatedtasks/"  # type: ignore
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(AutomatedTask.objects.filter(pk=policy_task.id))  # type: ignore
        delete_policy_autotasks_task.assert_called_with(task=policy_task.id)  # type: ignore

        self.check_not_authenticated("delete", url)

    @patch("autotasks.tasks.run_win_task.delay")
    def test_run_autotask(self, run_win_task):
        # setup data
        agent = baker.make_recipe("agents.agent", version="1.1.0")
        task = baker.make("autotasks.AutomatedTask", agent=agent)

        # test invalid url
        resp = self.client.get("/tasks/runwintask/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        # test run agent task
        url = f"/tasks/runwintask/{task.id}/"  # type: ignore
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        run_win_task.assert_called()

        self.check_not_authenticated("get", url)


class TestAutoTaskCeleryTasks(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("agents.models.Agent.nats_cmd")
    def test_remove_orphaned_win_task(self, nats_cmd):
        self.agent = baker.make_recipe("agents.agent")
        self.task1 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 1",
            win_task_name=AutomatedTask.generate_task_name(),
        )

        # test removing an orphaned task
        win_tasks = [
            "Adobe Acrobat Update Task",
            "AdobeGCInvoker-1.0",
            "GoogleUpdateTaskMachineCore",
            "GoogleUpdateTaskMachineUA",
            "OneDrive Standalone Update Task-S-1-5-21-717461175-241712648-1206041384-1001",
            self.task1.win_task_name,
            "TacticalRMM_fixmesh",
            "TacticalRMM_SchedReboot_jk324kajd",
            "TacticalRMM_iggrLcOaldIZnUzLuJWPLNwikiOoJJHHznb",  # orphaned task
        ]

        self.calls = [
            call({"func": "listschedtasks"}, timeout=10),
            call(
                {
                    "func": "delschedtask",
                    "schedtaskpayload": {
                        "name": "TacticalRMM_iggrLcOaldIZnUzLuJWPLNwikiOoJJHHznb"
                    },
                },
                timeout=10,
            ),
        ]

        nats_cmd.side_effect = [win_tasks, "ok"]
        ret = remove_orphaned_win_tasks.s(self.agent.pk).apply()
        self.assertEqual(nats_cmd.call_count, 2)
        nats_cmd.assert_has_calls(self.calls)
        self.assertEqual(ret.status, "SUCCESS")

        # test nats delete task fail
        nats_cmd.reset_mock()
        nats_cmd.side_effect = [win_tasks, "error deleting task"]
        ret = remove_orphaned_win_tasks.s(self.agent.pk).apply()
        nats_cmd.assert_has_calls(self.calls)
        self.assertEqual(nats_cmd.call_count, 2)
        self.assertEqual(ret.status, "SUCCESS")

        # no orphaned tasks
        nats_cmd.reset_mock()
        win_tasks.remove("TacticalRMM_iggrLcOaldIZnUzLuJWPLNwikiOoJJHHznb")
        nats_cmd.side_effect = [win_tasks, "ok"]
        ret = remove_orphaned_win_tasks.s(self.agent.pk).apply()
        self.assertEqual(nats_cmd.call_count, 1)
        self.assertEqual(ret.status, "SUCCESS")

    @patch("agents.models.Agent.nats_cmd")
    def test_run_win_task(self, nats_cmd):
        self.agent = baker.make_recipe("agents.agent")
        self.task1 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 1",
            win_task_name=AutomatedTask.generate_task_name(),
        )
        nats_cmd.return_value = "ok"
        ret = run_win_task.s(self.task1.pk).apply()
        self.assertEqual(ret.status, "SUCCESS")

    @patch("agents.models.Agent.nats_cmd")
    def test_create_win_task_schedule(self, nats_cmd):
        self.agent = baker.make_recipe("agents.agent")

        task_name = AutomatedTask.generate_task_name()
        # test scheduled task
        self.task1 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 1",
            win_task_name=task_name,
            task_type="scheduled",
            run_time_bit_weekdays=127,
            run_time_minute="21:55",
        )
        self.assertEqual(self.task1.sync_status, "initial")
        nats_cmd.return_value = "ok"
        ret = create_win_task_schedule.s(pk=self.task1.pk).apply()
        self.assertEqual(nats_cmd.call_count, 1)
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "type": "rmm",
                    "trigger": "weekly",
                    "weekdays": 127,
                    "pk": self.task1.pk,
                    "name": task_name,
                    "hour": 21,
                    "min": 55,
                },
            },
            timeout=5,
        )
        self.task1 = AutomatedTask.objects.get(pk=self.task1.pk)
        self.assertEqual(self.task1.sync_status, "synced")

        nats_cmd.return_value = "timeout"
        ret = create_win_task_schedule.s(pk=self.task1.pk).apply()
        self.assertEqual(ret.status, "SUCCESS")
        self.task1 = AutomatedTask.objects.get(pk=self.task1.pk)
        self.assertEqual(self.task1.sync_status, "initial")

        # test runonce with future date
        nats_cmd.reset_mock()
        task_name = AutomatedTask.generate_task_name()
        run_time_date = djangotime.now() + djangotime.timedelta(hours=22)
        self.task2 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 2",
            win_task_name=task_name,
            task_type="runonce",
            run_time_date=run_time_date,
        )
        nats_cmd.return_value = "ok"
        ret = create_win_task_schedule.s(pk=self.task2.pk).apply()
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "type": "rmm",
                    "trigger": "once",
                    "pk": self.task2.pk,
                    "name": task_name,
                    "year": int(dt.datetime.strftime(self.task2.run_time_date, "%Y")),
                    "month": dt.datetime.strftime(self.task2.run_time_date, "%B"),
                    "day": int(dt.datetime.strftime(self.task2.run_time_date, "%d")),
                    "hour": int(dt.datetime.strftime(self.task2.run_time_date, "%H")),
                    "min": int(dt.datetime.strftime(self.task2.run_time_date, "%M")),
                },
            },
            timeout=5,
        )
        self.assertEqual(ret.status, "SUCCESS")

        # test runonce with date in the past
        nats_cmd.reset_mock()
        task_name = AutomatedTask.generate_task_name()
        run_time_date = djangotime.now() - djangotime.timedelta(days=13)
        self.task3 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 3",
            win_task_name=task_name,
            task_type="runonce",
            run_time_date=run_time_date,
        )
        nats_cmd.return_value = "ok"
        ret = create_win_task_schedule.s(pk=self.task3.pk).apply()
        self.task3 = AutomatedTask.objects.get(pk=self.task3.pk)
        self.assertEqual(ret.status, "SUCCESS")

        # test checkfailure
        nats_cmd.reset_mock()
        self.check = baker.make_recipe("checks.diskspace_check", agent=self.agent)
        task_name = AutomatedTask.generate_task_name()
        self.task4 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 4",
            win_task_name=task_name,
            task_type="checkfailure",
            assigned_check=self.check,
        )
        nats_cmd.return_value = "ok"
        ret = create_win_task_schedule.s(pk=self.task4.pk).apply()
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "type": "rmm",
                    "trigger": "manual",
                    "pk": self.task4.pk,
                    "name": task_name,
                },
            },
            timeout=5,
        )
        self.assertEqual(ret.status, "SUCCESS")

        # test manual
        nats_cmd.reset_mock()
        task_name = AutomatedTask.generate_task_name()
        self.task5 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 5",
            win_task_name=task_name,
            task_type="manual",
        )
        nats_cmd.return_value = "ok"
        ret = create_win_task_schedule.s(pk=self.task5.pk).apply()
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "type": "rmm",
                    "trigger": "manual",
                    "pk": self.task5.pk,
                    "name": task_name,
                },
            },
            timeout=5,
        )
        self.assertEqual(ret.status, "SUCCESS")
