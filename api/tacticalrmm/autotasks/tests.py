from unittest.mock import patch, call
from model_bakery import baker
from django.utils import timezone as djangotime

from tacticalrmm.test import TacticalTestCase

from .models import AutomatedTask
from logs.models import PendingAction
from .serializers import AutoTaskSerializer
from .tasks import remove_orphaned_win_tasks, run_win_task, create_win_task_schedule


class TestAutotaskViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("automation.tasks.generate_agent_tasks_from_policies_task.delay")
    @patch("autotasks.tasks.create_win_task_schedule.delay")
    def test_add_autotask(
        self, create_win_task_schedule, generate_agent_tasks_from_policies_task
    ):
        url = "/tasks/automatedtasks/"

        # setup data
        script = baker.make_recipe("scripts.script")
        agent = baker.make_recipe("agents.agent")
        agent_old = baker.make_recipe("agents.agent", version="0.9.0")
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

        # test invalid agent version
        data = {
            "autotask": {"script": script.id, "script_args": ["args"]},
            "agent": agent_old.id,
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        # test add task to agent
        data = {
            "autotask": {
                "name": "Test Task Scheduled with Assigned Check",
                "run_time_days": [0, 1, 2],
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
                "timeout": 120,
                "enabled": True,
                "script": script.id,
                "script_args": None,
                "task_type": "manual",
                "assigned_check": None,
            },
            "policy": policy.id,
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        generate_agent_tasks_from_policies_task.assert_called_with(policy.id)

        self.check_not_authenticated("post", url)

    def test_get_autotask(self):

        # setup data
        agent = baker.make_recipe("agents.agent")
        baker.make("autotasks.AutomatedTask", agent=agent, _quantity=3)

        url = f"/tasks/{agent.id}/automatedtasks/"

        resp = self.client.get(url, format="json")
        serializer = AutoTaskSerializer(agent)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        self.check_not_authenticated("get", url)

    @patch("autotasks.tasks.enable_or_disable_win_task.delay")
    @patch("automation.tasks.update_policy_task_fields_task.delay")
    def test_update_autotask(
        self, update_policy_task_fields_task, enable_or_disable_win_task
    ):
        # setup data
        agent = baker.make_recipe("agents.agent")
        agent_task = baker.make("autotasks.AutomatedTask", agent=agent)
        policy = baker.make("automation.Policy")
        policy_task = baker.make("autotasks.AutomatedTask", policy=policy)

        # test invalid url
        resp = self.client.patch("/tasks/500/automatedtasks/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"/tasks/{agent_task.id}/automatedtasks/"

        # test editing agent task
        data = {"enableordisable": False}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        enable_or_disable_win_task.assert_called_with(pk=agent_task.id, action=False)

        url = f"/tasks/{policy_task.id}/automatedtasks/"

        # test editing policy task
        data = {"enableordisable": True}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        update_policy_task_fields_task.assert_called_with(policy_task.id, True)

        self.check_not_authenticated("patch", url)

    @patch("autotasks.tasks.delete_win_task_schedule.delay")
    @patch("automation.tasks.delete_policy_autotask_task.delay")
    def test_delete_autotask(
        self, delete_policy_autotask_task, delete_win_task_schedule
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
        url = f"/tasks/{agent_task.id}/automatedtasks/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)
        delete_win_task_schedule.assert_called_with(pk=agent_task.id)

        # test delete policy task
        url = f"/tasks/{policy_task.id}/automatedtasks/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)
        delete_policy_autotask_task.assert_called_with(policy_task.id)

        self.check_not_authenticated("delete", url)

    @patch("autotasks.tasks.run_win_task.delay")
    def test_run_autotask(self, run_win_task):
        # setup data
        agent = baker.make_recipe("agents.agent")
        task = baker.make("autotasks.AutomatedTask", agent=agent)

        # test invalid url
        resp = self.client.get("/tasks/runwintask/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        # test run agent task
        url = f"/tasks/runwintask/{task.id}/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        run_win_task.assert_called_with(task.id)

        self.check_not_authenticated("get", url)


class TestAutoTaskCeleryTasks(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("agents.models.Agent.salt_api_cmd")
    def test_remove_orphaned_win_task(self, salt_api_cmd):
        self.agent = baker.make_recipe("agents.agent")
        self.task1 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 1",
            win_task_name=AutomatedTask.generate_task_name(),
        )

        salt_api_cmd.return_value = "timeout"
        ret = remove_orphaned_win_tasks.s(self.agent.pk).apply()
        self.assertEqual(ret.result, "errtimeout")

        salt_api_cmd.return_value = "error"
        ret = remove_orphaned_win_tasks.s(self.agent.pk).apply()
        self.assertEqual(ret.result, "errtimeout")

        salt_api_cmd.return_value = "task not found in"
        ret = remove_orphaned_win_tasks.s(self.agent.pk).apply()
        self.assertEqual(ret.result, "notlist")

        salt_api_cmd.reset_mock()

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
            call(timeout=15, func="task.list_tasks"),
            call(
                timeout=20,
                func="task.delete_task",
                arg=["name=TacticalRMM_iggrLcOaldIZnUzLuJWPLNwikiOoJJHHznb"],
            ),
        ]

        salt_api_cmd.side_effect = [win_tasks, True]
        ret = remove_orphaned_win_tasks.s(self.agent.pk).apply()
        self.assertEqual(salt_api_cmd.call_count, 2)
        salt_api_cmd.assert_has_calls(self.calls)
        self.assertEqual(ret.status, "SUCCESS")

        # test salt delete_task fail
        salt_api_cmd.reset_mock()
        salt_api_cmd.side_effect = [win_tasks, False]
        ret = remove_orphaned_win_tasks.s(self.agent.pk).apply()
        salt_api_cmd.assert_has_calls(self.calls)
        self.assertEqual(salt_api_cmd.call_count, 2)
        self.assertEqual(ret.status, "SUCCESS")

        # no orphaned tasks
        salt_api_cmd.reset_mock()
        win_tasks.remove("TacticalRMM_iggrLcOaldIZnUzLuJWPLNwikiOoJJHHznb")
        salt_api_cmd.side_effect = [win_tasks, True]
        ret = remove_orphaned_win_tasks.s(self.agent.pk).apply()
        self.assertEqual(salt_api_cmd.call_count, 1)
        self.assertEqual(ret.status, "SUCCESS")

    @patch("agents.models.Agent.salt_api_async")
    def test_run_win_task(self, salt_api_async):
        self.agent = baker.make_recipe("agents.agent")
        self.task1 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 1",
            win_task_name=AutomatedTask.generate_task_name(),
        )
        salt_api_async.return_value = "Response 200"
        ret = run_win_task.s(self.task1.pk).apply()
        self.assertEqual(ret.status, "SUCCESS")

    @patch("agents.models.Agent.salt_api_cmd")
    def test_create_win_task_schedule(self, salt_api_cmd):
        self.agent = baker.make_recipe("agents.agent")

        task_name = AutomatedTask.generate_task_name()
        # test scheduled task
        self.task1 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 1",
            win_task_name=task_name,
            task_type="scheduled",
            run_time_days=[0, 1, 6],
            run_time_minute="21:55",
        )
        self.assertEqual(self.task1.sync_status, "notsynced")
        salt_api_cmd.return_value = True
        ret = create_win_task_schedule.s(pk=self.task1.pk, pending_action=False).apply()
        self.assertEqual(salt_api_cmd.call_count, 1)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="task.create_task",
            arg=[
                f"name={task_name}",
                "force=True",
                "action_type=Execute",
                'cmd="C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"',
                f'arguments="-m taskrunner -p {self.task1.pk}"',
                "start_in=C:\\Program Files\\TacticalAgent",
                "trigger_type=Weekly",
                'start_time="21:55"',
                "ac_only=False",
                "stop_if_on_batteries=False",
            ],
            kwargs={"days_of_week": ["Monday", "Tuesday", "Sunday"]},
        )
        self.task1 = AutomatedTask.objects.get(pk=self.task1.pk)
        self.assertEqual(self.task1.sync_status, "synced")

        salt_api_cmd.return_value = "timeout"
        ret = create_win_task_schedule.s(pk=self.task1.pk, pending_action=False).apply()
        self.assertEqual(ret.status, "SUCCESS")
        self.task1 = AutomatedTask.objects.get(pk=self.task1.pk)
        self.assertEqual(self.task1.sync_status, "notsynced")

        salt_api_cmd.return_value = "error"
        ret = create_win_task_schedule.s(pk=self.task1.pk, pending_action=False).apply()
        self.assertEqual(ret.status, "SUCCESS")
        self.task1 = AutomatedTask.objects.get(pk=self.task1.pk)
        self.assertEqual(self.task1.sync_status, "notsynced")

        salt_api_cmd.return_value = False
        ret = create_win_task_schedule.s(pk=self.task1.pk, pending_action=False).apply()
        self.assertEqual(ret.status, "SUCCESS")
        self.task1 = AutomatedTask.objects.get(pk=self.task1.pk)
        self.assertEqual(self.task1.sync_status, "notsynced")

        # test pending action
        self.pending_action = PendingAction.objects.create(
            agent=self.agent, action_type="taskaction"
        )
        self.assertEqual(self.pending_action.status, "pending")
        salt_api_cmd.return_value = True
        ret = create_win_task_schedule.s(
            pk=self.task1.pk, pending_action=self.pending_action.pk
        ).apply()
        self.assertEqual(ret.status, "SUCCESS")
        self.pending_action = PendingAction.objects.get(pk=self.pending_action.pk)
        self.assertEqual(self.pending_action.status, "completed")

        # test runonce with future date
        salt_api_cmd.reset_mock()
        task_name = AutomatedTask.generate_task_name()
        run_time_date = djangotime.now() + djangotime.timedelta(hours=22)
        self.task2 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 2",
            win_task_name=task_name,
            task_type="runonce",
            run_time_date=run_time_date,
        )
        salt_api_cmd.return_value = True
        ret = create_win_task_schedule.s(pk=self.task2.pk, pending_action=False).apply()
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="task.create_task",
            arg=[
                f"name={task_name}",
                "force=True",
                "action_type=Execute",
                'cmd="C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"',
                f'arguments="-m taskrunner -p {self.task2.pk}"',
                "start_in=C:\\Program Files\\TacticalAgent",
                "trigger_type=Once",
                f'start_date="{run_time_date.strftime("%Y-%m-%d")}"',
                f'start_time="{run_time_date.strftime("%H:%M")}"',
                "ac_only=False",
                "stop_if_on_batteries=False",
                "start_when_available=True",
            ],
        )
        self.assertEqual(ret.status, "SUCCESS")

        # test runonce with date in the past
        salt_api_cmd.reset_mock()
        task_name = AutomatedTask.generate_task_name()
        run_time_date = djangotime.now() - djangotime.timedelta(days=13)
        self.task3 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 3",
            win_task_name=task_name,
            task_type="runonce",
            run_time_date=run_time_date,
        )
        salt_api_cmd.return_value = True
        ret = create_win_task_schedule.s(pk=self.task3.pk, pending_action=False).apply()
        self.task3 = AutomatedTask.objects.get(pk=self.task3.pk)
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="task.create_task",
            arg=[
                f"name={task_name}",
                "force=True",
                "action_type=Execute",
                'cmd="C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"',
                f'arguments="-m taskrunner -p {self.task3.pk}"',
                "start_in=C:\\Program Files\\TacticalAgent",
                "trigger_type=Once",
                f'start_date="{self.task3.run_time_date.strftime("%Y-%m-%d")}"',
                f'start_time="{self.task3.run_time_date.strftime("%H:%M")}"',
                "ac_only=False",
                "stop_if_on_batteries=False",
                "start_when_available=True",
            ],
        )
        self.assertEqual(ret.status, "SUCCESS")

        # test checkfailure
        salt_api_cmd.reset_mock()
        self.check = baker.make_recipe("checks.diskspace_check", agent=self.agent)
        task_name = AutomatedTask.generate_task_name()
        self.task4 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 4",
            win_task_name=task_name,
            task_type="checkfailure",
            assigned_check=self.check,
        )
        salt_api_cmd.return_value = True
        ret = create_win_task_schedule.s(pk=self.task4.pk, pending_action=False).apply()
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="task.create_task",
            arg=[
                f"name={task_name}",
                "force=True",
                "action_type=Execute",
                'cmd="C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"',
                f'arguments="-m taskrunner -p {self.task4.pk}"',
                "start_in=C:\\Program Files\\TacticalAgent",
                "trigger_type=Once",
                'start_date="1975-01-01"',
                'start_time="01:00"',
                "ac_only=False",
                "stop_if_on_batteries=False",
            ],
        )
        self.assertEqual(ret.status, "SUCCESS")

        # test manual
        salt_api_cmd.reset_mock()
        task_name = AutomatedTask.generate_task_name()
        self.task5 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 5",
            win_task_name=task_name,
            task_type="manual",
        )
        salt_api_cmd.return_value = True
        ret = create_win_task_schedule.s(pk=self.task5.pk, pending_action=False).apply()
        salt_api_cmd.assert_called_with(
            timeout=20,
            func="task.create_task",
            arg=[
                f"name={task_name}",
                "force=True",
                "action_type=Execute",
                'cmd="C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"',
                f'arguments="-m taskrunner -p {self.task5.pk}"',
                "start_in=C:\\Program Files\\TacticalAgent",
                "trigger_type=Once",
                'start_date="1975-01-01"',
                'start_time="01:00"',
                "ac_only=False",
                "stop_if_on_batteries=False",
            ],
        )
        self.assertEqual(ret.status, "SUCCESS")
