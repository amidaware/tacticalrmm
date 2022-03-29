from unittest.mock import call, patch

from django.utils import timezone as djangotime
from model_bakery import baker

from tacticalrmm.test import TacticalTestCase

from .models import AutomatedTask
from .serializers import TaskSerializer
from .tasks import remove_orphaned_win_tasks, run_win_task

base_url = "/tasks"


class TestAutotaskViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_get_autotasks(self):
        # setup data
        agent = baker.make_recipe("agents.agent")
        baker.make("autotasks.AutomatedTask", agent=agent, _quantity=3)
        policy = baker.make("automation.Policy")
        baker.make("autotasks.AutomatedTask", policy=policy, _quantity=4)
        baker.make("autotasks.AutomatedTask", _quantity=7)

        # test returning all tasks
        url = f"{base_url}/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 14)  # type: ignore

        # test returning tasks for a specific agent
        url = f"/agents/{agent.agent_id}/tasks/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 3)  # type: ignore

        # test returning tasks for a specific policy
        url = f"/automation/policies/{policy.id}/tasks/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 4)  # type: ignore

    @patch("autotasks.tasks.create_win_task_schedule.delay")
    def test_add_autotask(self, create_win_task_schedule):
        url = f"{base_url}/"

        # setup data
        script = baker.make_recipe("scripts.script")
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        check = baker.make_recipe("checks.diskspace_check", agent=agent)
        custom_field = baker.make("core.CustomField")

        actions = [
            {"type": "cmd", "command": "command", "timeout": 30},
            {"type": "script", "script": script.id, "script_args": [], "timeout": 90},
        ]

        # test invalid agent
        data = {
            "agent": "13kfs89as9d89asd8f98df8df8dfhdf",
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 404)

        # test add task without actions
        data = {
            "agent": agent.agent_id,
            "name": "Test Task Scheduled with Assigned Check",
            "run_time_days": 56,
            "enabled": True,
            "actions": [],
            "task_type": "manual",
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        # test add checkfailure task_type to agent without check
        data = {
            "agent": agent.agent_id,
            "name": "Check Failure",
            "enabled": True,
            "actions": actions,
            "task_type": "checkfailure",
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        create_win_task_schedule.not_assert_called()

        # test add manual task_type to agent
        data = {
            "agent": agent.agent_id,
            "name": "Manual",
            "enabled": True,
            "actions": actions,
            "task_type": "manual",
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        create_win_task_schedule.assert_called()
        create_win_task_schedule.reset_mock()

        # test add daily task_type to agent
        data = {
            "agent": agent.agent_id,
            "name": "Daily",
            "enabled": True,
            "actions": actions,
            "task_type": "daily",
            "daily_interval": 1,
            "run_time_date": djangotime.now(),
            "repetition_interval": "30M",
            "repetition_duration": "1D",
            "random_task_delay": "5M",
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        # test add weekly task_type to agent
        data = {
            "agent": agent.agent_id,
            "name": "Weekly",
            "enabled": True,
            "actions": actions,
            "task_type": "weekly",
            "weekly_interval": 2,
            "run_time_bit_weekdays": 26,
            "run_time_date": djangotime.now(),
            "expire_date": djangotime.now(),
            "repetition_interval": "30S",
            "repetition_duration": "1H",
            "random_task_delay": "5M",
            "task_instance_policy": 2,
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        create_win_task_schedule.assert_called()
        create_win_task_schedule.reset_mock()

        # test add monthly task_type to agent
        data = {
            "agent": agent.agent_id,
            "name": "Monthly",
            "enabled": True,
            "actions": actions,
            "task_type": "monthly",
            "monthly_months_of_year": 56,
            "monthly_days_of_month": 350,
            "run_time_date": djangotime.now(),
            "expire_date": djangotime.now(),
            "repetition_interval": "30S",
            "repetition_duration": "1H",
            "random_task_delay": "5M",
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        create_win_task_schedule.assert_called()
        create_win_task_schedule.reset_mock()

        # test add monthly day-of-week task_type to agent
        data = {
            "agent": agent.agent_id,
            "name": "Monthly",
            "enabled": True,
            "actions": actions,
            "task_type": "monthlydow",
            "monthly_months_of_year": 500,
            "monthly_weeks_of_month": 4,
            "run_time_bit_weekdays": 15,
            "run_time_date": djangotime.now(),
            "expire_date": djangotime.now(),
            "repetition_interval": "30S",
            "repetition_duration": "1H",
            "random_task_delay": "5M",
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        create_win_task_schedule.assert_called()
        create_win_task_schedule.reset_mock()

        # test add monthly day-of-week task_type to agent with custom field
        data = {
            "agent": agent.agent_id,
            "name": "Monthly",
            "enabled": True,
            "actions": actions,
            "task_type": "monthlydow",
            "monthly_months_of_year": 500,
            "monthly_weeks_of_month": 4,
            "run_time_bit_weekdays": 15,
            "run_time_date": djangotime.now(),
            "expire_date": djangotime.now(),
            "repetition_interval": "30S",
            "repetition_duration": "1H",
            "random_task_delay": "5M",
            "custom_field": custom_field.id,
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        create_win_task_schedule.assert_called()
        create_win_task_schedule.reset_mock()

        # test add checkfailure task_type to agent
        data = {
            "agent": agent.agent_id,
            "name": "Check Failure",
            "enabled": True,
            "actions": actions,
            "task_type": "checkfailure",
            "assigned_check": check.id,
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        create_win_task_schedule.assert_called()
        create_win_task_schedule.reset_mock()

        self.check_not_authenticated("post", url)

    def test_get_autotask(self):

        # setup data
        agent = baker.make_recipe("agents.agent")
        task = baker.make("autotasks.AutomatedTask", agent=agent)

        url = f"{base_url}/{task.id}/"

        resp = self.client.get(url, format="json")
        serializer = TaskSerializer(task)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_update_autotask(self):
        # setup data
        agent = baker.make_recipe("agents.agent")
        agent_task = baker.make("autotasks.AutomatedTask", agent=agent)
        policy = baker.make("automation.Policy")
        policy_task = baker.make("autotasks.AutomatedTask", enabled=True, policy=policy)
        custom_field = baker.make("core.CustomField")
        script = baker.make("scripts.Script")

        actions = [
            {"type": "cmd", "command": "command", "timeout": 30},
            {"type": "script", "script": script.id, "script_args": [], "timeout": 90},
        ]

        # test invalid url
        resp = self.client.put(f"{base_url}/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"{base_url}/{agent_task.id}/"  # type: ignore

        # test editing agent task with no task update
        data = {"name": "New Name"}

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        # test editing agent task with agent task update
        data = {"enabled": False}

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        # test editing agent task with task_type
        data = {
            "name": "Monthly",
            "actions": actions,
            "task_type": "monthlydow",
            "monthly_months_of_year": 500,
            "monthly_weeks_of_month": 4,
            "run_time_bit_weekdays": 15,
            "run_time_date": djangotime.now(),
            "expire_date": djangotime.now(),
            "repetition_interval": "30S",
            "repetition_duration": "1H",
            "random_task_delay": "5M",
            "custom_field": custom_field.id,
            "run_asap_afteR_missed": False,
        }

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        # test trying to edit with empty actions
        data = {
            "name": "Monthly",
            "actions": [],
            "task_type": "monthlydow",
            "monthly_months_of_year": 500,
            "monthly_weeks_of_month": 4,
            "run_time_bit_weekdays": 15,
            "run_time_date": djangotime.now(),
            "expire_date": djangotime.now(),
            "repetition_interval": "30S",
            "repetition_duration": "1H",
            "random_task_delay": "5M",
            "run_asap_afteR_missed": False,
        }

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("put", url)

    @patch("autotasks.tasks.delete_win_task_schedule.delay")
    def test_delete_autotask(self, delete_win_task_schedule):
        # setup data
        agent = baker.make_recipe("agents.agent")
        agent_task = baker.make("autotasks.AutomatedTask", agent=agent)
        policy = baker.make("automation.Policy")
        policy_task = baker.make("autotasks.AutomatedTask", policy=policy)

        # test invalid url
        resp = self.client.delete(f"{base_url}/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        # test delete agent task
        url = f"{base_url}/{agent_task.id}/"  # type: ignore
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)
        delete_win_task_schedule.assert_called_with(pk=agent_task.id)  # type: ignore

        self.check_not_authenticated("delete", url)

    @patch("autotasks.tasks.run_win_task.delay")
    def test_run_autotask(self, run_win_task):
        # setup data
        agent = baker.make_recipe("agents.agent", version="1.1.0")
        task = baker.make("autotasks.AutomatedTask", agent=agent)

        # test invalid url
        resp = self.client.post(f"{base_url}/500/run/", format="json")
        self.assertEqual(resp.status_code, 404)

        # test run agent task
        url = f"{base_url}/{task.id}/run/"  # type: ignore
        resp = self.client.post(url, format="json")
        self.assertEqual(resp.status_code, 200)
        run_win_task.assert_called()

        self.check_not_authenticated("post", url)


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

    # @patch("agents.models.Agent.nats_cmd")
    # def test_create_win_task_schedule(self, nats_cmd):
    #     self.agent = baker.make_recipe("agents.agent")

    #     task_name = AutomatedTask.generate_task_name()
    #     # test scheduled task
    #     self.task1 = AutomatedTask.objects.create(
    #         agent=self.agent,
    #         name="test task 1",
    #         win_task_name=task_name,
    #         task_type="scheduled",
    #         run_time_bit_weekdays=127,
    #         run_time_minute="21:55",
    #     )
    #     self.assertEqual(self.task1.sync_status, "initial")
    #     nats_cmd.return_value = "ok"
    #     ret = create_win_task_schedule.s(pk=self.task1.pk).apply()
    #     self.assertEqual(nats_cmd.call_count, 1)
    #     nats_cmd.assert_called_with(
    #         {
    #             "func": "schedtask",
    #             "schedtaskpayload": {
    #                 "type": "rmm",
    #                 "trigger": "weekly",
    #                 "weekdays": 127,
    #                 "pk": self.task1.pk,
    #                 "name": task_name,
    #                 "hour": 21,
    #                 "min": 55,
    #             },
    #         },
    #         timeout=5,
    #     )
    #     self.task1 = AutomatedTask.objects.get(pk=self.task1.pk)
    #     self.assertEqual(self.task1.sync_status, "synced")

    #     nats_cmd.return_value = "timeout"
    #     ret = create_win_task_schedule.s(pk=self.task1.pk).apply()
    #     self.assertEqual(ret.status, "SUCCESS")
    #     self.task1 = AutomatedTask.objects.get(pk=self.task1.pk)
    #     self.assertEqual(self.task1.sync_status, "initial")

    #     # test runonce with future date
    #     nats_cmd.reset_mock()
    #     task_name = AutomatedTask.generate_task_name()
    #     run_time_date = djangotime.now() + djangotime.timedelta(hours=22)
    #     self.task2 = AutomatedTask.objects.create(
    #         agent=self.agent,
    #         name="test task 2",
    #         win_task_name=task_name,
    #         task_type="runonce",
    #         run_time_date=run_time_date,
    #     )
    #     nats_cmd.return_value = "ok"
    #     ret = create_win_task_schedule.s(pk=self.task2.pk).apply()
    #     nats_cmd.assert_called_with(
    #         {
    #             "func": "schedtask",
    #             "schedtaskpayload": {
    #                 "type": "rmm",
    #                 "trigger": "once",
    #                 "pk": self.task2.pk,
    #                 "name": task_name,
    #                 "year": int(dt.datetime.strftime(self.task2.run_time_date, "%Y")),
    #                 "month": dt.datetime.strftime(self.task2.run_time_date, "%B"),
    #                 "day": int(dt.datetime.strftime(self.task2.run_time_date, "%d")),
    #                 "hour": int(dt.datetime.strftime(self.task2.run_time_date, "%H")),
    #                 "min": int(dt.datetime.strftime(self.task2.run_time_date, "%M")),
    #             },
    #         },
    #         timeout=5,
    #     )
    #     self.assertEqual(ret.status, "SUCCESS")

    #     # test runonce with date in the past
    #     nats_cmd.reset_mock()
    #     task_name = AutomatedTask.generate_task_name()
    #     run_time_date = djangotime.now() - djangotime.timedelta(days=13)
    #     self.task3 = AutomatedTask.objects.create(
    #         agent=self.agent,
    #         name="test task 3",
    #         win_task_name=task_name,
    #         task_type="runonce",
    #         run_time_date=run_time_date,
    #     )
    #     nats_cmd.return_value = "ok"
    #     ret = create_win_task_schedule.s(pk=self.task3.pk).apply()
    #     self.task3 = AutomatedTask.objects.get(pk=self.task3.pk)
    #     self.assertEqual(ret.status, "SUCCESS")

    #     # test checkfailure
    #     nats_cmd.reset_mock()
    #     self.check = baker.make_recipe("checks.diskspace_check", agent=self.agent)
    #     task_name = AutomatedTask.generate_task_name()
    #     self.task4 = AutomatedTask.objects.create(
    #         agent=self.agent,
    #         name="test task 4",
    #         win_task_name=task_name,
    #         task_type="checkfailure",
    #         assigned_check=self.check,
    #     )
    #     nats_cmd.return_value = "ok"
    #     ret = create_win_task_schedule.s(pk=self.task4.pk).apply()
    #     nats_cmd.assert_called_with(
    #         {
    #             "func": "schedtask",
    #             "schedtaskpayload": {
    #                 "type": "rmm",
    #                 "trigger": "manual",
    #                 "pk": self.task4.pk,
    #                 "name": task_name,
    #             },
    #         },
    #         timeout=5,
    #     )
    #     self.assertEqual(ret.status, "SUCCESS")

    #     # test manual
    #     nats_cmd.reset_mock()
    #     task_name = AutomatedTask.generate_task_name()
    #     self.task5 = AutomatedTask.objects.create(
    #         agent=self.agent,
    #         name="test task 5",
    #         win_task_name=task_name,
    #         task_type="manual",
    #     )
    #     nats_cmd.return_value = "ok"
    #     ret = create_win_task_schedule.s(pk=self.task5.pk).apply()
    #     nats_cmd.assert_called_with(
    #         {
    #             "func": "schedtask",
    #             "schedtaskpayload": {
    #                 "type": "rmm",
    #                 "trigger": "manual",
    #                 "pk": self.task5.pk,
    #                 "name": task_name,
    #             },
    #         },
    #         timeout=5,
    #     )
    #     self.assertEqual(ret.status, "SUCCESS")


class TestTaskPermissions(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.client_setup()

    def test_get_tasks_permissions(self):
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        unauthorized_agent = baker.make_recipe("agents.agent")
        task = baker.make("autotasks.AutomatedTask", agent=agent, _quantity=5)
        unauthorized_task = baker.make(
            "autotasks.AutomatedTask", agent=unauthorized_agent, _quantity=7
        )

        policy_tasks = baker.make("autotasks.AutomatedTask", policy=policy, _quantity=2)

        # test super user access
        self.check_authorized_superuser("get", f"{base_url}/")
        self.check_authorized_superuser("get", f"/agents/{agent.agent_id}/tasks/")
        self.check_authorized_superuser(
            "get", f"/agents/{unauthorized_agent.agent_id}/tasks/"
        )
        self.check_authorized_superuser(
            "get", f"/automation/policies/{policy.id}/tasks/"
        )

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)  # type: ignore

        self.check_not_authorized("get", f"{base_url}/")
        self.check_not_authorized("get", f"/agents/{agent.agent_id}/tasks/")
        self.check_not_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/tasks/"
        )
        self.check_not_authorized("get", f"/automation/policies/{policy.id}/tasks/")

        # add list software role to user
        user.role.can_list_autotasks = True
        user.role.save()

        r = self.check_authorized("get", f"{base_url}/")
        self.assertEqual(len(r.data), 14)  # type: ignore
        r = self.check_authorized("get", f"/agents/{agent.agent_id}/tasks/")
        self.assertEqual(len(r.data), 5)  # type: ignore
        r = self.check_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/tasks/"
        )
        self.assertEqual(len(r.data), 7)  # type: ignore
        r = self.check_authorized("get", f"/automation/policies/{policy.id}/tasks/")
        self.assertEqual(len(r.data), 2)  # type: ignore

        # test limiting to client
        user.role.can_view_clients.set([agent.client])
        self.check_not_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/tasks/"
        )
        self.check_authorized("get", f"/agents/{agent.agent_id}/tasks/")
        self.check_authorized("get", f"/automation/policies/{policy.id}/tasks/")

        # make sure queryset is limited too
        r = self.client.get(f"{base_url}/")
        self.assertEqual(len(r.data), 7)  # type: ignore

    def test_add_task_permissions(self):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        script = baker.make("scripts.Script")

        policy_data = {
            "policy": policy.id,  # type: ignore
            "name": "Test Task Manual",
            "run_time_days": [],
            "timeout": 120,
            "enabled": True,
            "script": script.id,
            "script_args": [],
            "task_type": "manual",
            "assigned_check": None,
        }

        agent_data = {
            "agent": agent.agent_id,
            "name": "Test Task Manual",
            "run_time_days": [],
            "timeout": 120,
            "enabled": True,
            "script": script.id,
            "script_args": [],
            "task_type": "manual",
            "assigned_check": None,
        }

        unauthorized_agent_data = {
            "agent": unauthorized_agent.agent_id,
            "name": "Test Task Manual",
            "run_time_days": [],
            "timeout": 120,
            "enabled": True,
            "script": script.id,
            "script_args": [],
            "task_type": "manual",
            "assigned_check": None,
        }

        url = f"{base_url}/"

        for data in [policy_data, agent_data]:
            # test superuser access
            self.check_authorized_superuser("post", url, data)

            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)  # type: ignore

            # test user without role
            self.check_not_authorized("post", url, data)

            # add user to role and test
            setattr(user.role, "can_manage_autotasks", True)
            user.role.save()

            self.check_authorized("post", url, data)

            # limit user to client
            user.role.can_view_clients.set([agent.client])
            if "agent" in data.keys():
                self.check_authorized("post", url, data)
                self.check_not_authorized("post", url, unauthorized_agent_data)
            else:
                self.check_authorized("post", url, data)

    # mock the task delete method so it actually isn't deleted
    @patch("autotasks.models.AutomatedTask.delete")
    def test_task_get_edit_delete_permissions(self, delete_task):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        task = baker.make("autotasks.AutomatedTask", agent=agent)
        unauthorized_task = baker.make(
            "autotasks.AutomatedTask", agent=unauthorized_agent
        )
        policy_task = baker.make("autotasks.AutomatedTask", policy=policy)

        for method in ["get", "put", "delete"]:

            url = f"{base_url}/{task.id}/"
            unauthorized_url = f"{base_url}/{unauthorized_task.id}/"
            policy_url = f"{base_url}/{policy_task.id}/"

            # test superuser access
            self.check_authorized_superuser(method, url)
            self.check_authorized_superuser(method, unauthorized_url)
            self.check_authorized_superuser(method, policy_url)

            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)  # type: ignore

            # test user without role
            self.check_not_authorized(method, url)
            self.check_not_authorized(method, unauthorized_url)
            self.check_not_authorized(method, policy_url)

            # add user to role and test
            setattr(
                user.role,
                "can_list_autotasks" if method == "get" else "can_manage_autotasks",
                True,
            )
            user.role.save()

            self.check_authorized(method, url)
            self.check_authorized(method, unauthorized_url)
            self.check_authorized(method, policy_url)

            # limit user to client if agent task
            user.role.can_view_clients.set([agent.client])

            self.check_authorized(method, url)
            self.check_not_authorized(method, unauthorized_url)
            self.check_authorized(method, policy_url)

    def test_task_action_permissions(self):

        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        task = baker.make("autotasks.AutomatedTask", agent=agent)
        unauthorized_task = baker.make(
            "autotasks.AutomatedTask", agent=unauthorized_agent
        )

        url = f"{base_url}/{task.id}/run/"
        unauthorized_url = f"{base_url}/{unauthorized_task.id}/run/"

        # test superuser access
        self.check_authorized_superuser("post", url)
        self.check_authorized_superuser("post", unauthorized_url)

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)  # type: ignore

        # test user without role
        self.check_not_authorized("post", url)
        self.check_not_authorized("post", unauthorized_url)

        # add user to role and test
        user.role.can_run_autotasks = True
        user.role.save()

        self.check_authorized("post", url)
        self.check_authorized("post", unauthorized_url)

        # limit user to client if agent task
        user.role.can_view_sites.set([agent.site])

        self.check_authorized("post", url)
        self.check_not_authorized("post", unauthorized_url)
