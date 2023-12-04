from unittest.mock import patch

from django.utils import timezone as djangotime
from model_bakery import baker

from tacticalrmm.constants import TaskType
from tacticalrmm.test import TacticalTestCase

from .models import AutomatedTask, TaskResult, TaskSyncStatus
from .serializers import TaskSerializer
from .tasks import create_win_task_schedule, run_win_task

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
        self.assertEqual(len(resp.data), 14)

        # test returning tasks for a specific agent
        url = f"/agents/{agent.agent_id}/tasks/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 3)

        # test returning tasks for a specific policy
        url = f"/automation/policies/{policy.id}/tasks/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 4)

    @patch("autotasks.tasks.create_win_task_schedule.delay")
    def test_add_autotask(self, create_win_task_schedule):
        url = f"{base_url}/"

        # setup data
        script = baker.make_recipe("scripts.script")
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")  # noqa
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
            "expire_date": djangotime.now() + djangotime.timedelta(weeks=5),
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
            "expire_date": djangotime.now() + djangotime.timedelta(weeks=5),
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
            "expire_date": djangotime.now() + djangotime.timedelta(weeks=5),
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
            "expire_date": djangotime.now() + djangotime.timedelta(weeks=5),
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
        self.assertEqual(resp.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_update_autotask(self):
        # setup data
        agent = baker.make_recipe("agents.agent")
        agent_task = baker.make("autotasks.AutomatedTask", agent=agent)
        policy = baker.make("automation.Policy")
        policy_task = baker.make(  # noqa
            "autotasks.AutomatedTask", enabled=True, policy=policy
        )
        custom_field = baker.make("core.CustomField")
        script = baker.make("scripts.Script")

        actions = [
            {"type": "cmd", "command": "command", "timeout": 30},
            {"type": "script", "script": script.id, "script_args": [], "timeout": 90},
        ]

        # test invalid url
        resp = self.client.put(f"{base_url}/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"{base_url}/{agent_task.id}/"

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
            "expire_date": djangotime.now() + djangotime.timedelta(weeks=5),
            "repetition_interval": "30S",
            "repetition_duration": "1H",
            "random_task_delay": "5M",
            "custom_field": custom_field.id,
            "run_asap_after_missed": False,
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
            "expire_date": djangotime.now() + djangotime.timedelta(weeks=5),
            "repetition_interval": "30S",
            "repetition_duration": "1H",
            "random_task_delay": "5M",
            "run_asap_afteR_missed": False,
        }

        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("put", url)

    @patch("autotasks.tasks.remove_orphaned_win_tasks.delay")
    @patch("autotasks.tasks.delete_win_task_schedule.delay")
    def test_delete_autotask(self, delete_win_task_schedule, remove_orphaned_win_tasks):
        # setup data
        agent = baker.make_recipe("agents.agent")
        agent_task = baker.make("autotasks.AutomatedTask", agent=agent)
        policy = baker.make("automation.Policy")
        policy_task = baker.make("autotasks.AutomatedTask", policy=policy)

        # test invalid url
        resp = self.client.delete(f"{base_url}/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        # test delete agent task
        url = f"{base_url}/{agent_task.id}/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)
        delete_win_task_schedule.assert_called_with(pk=agent_task.id)
        remove_orphaned_win_tasks.assert_not_called()

        delete_win_task_schedule.reset_mock()
        remove_orphaned_win_tasks.reset_mock()
        # test delete policy task
        url = f"{base_url}/{policy_task.id}/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)
        remove_orphaned_win_tasks.assert_called_once()
        delete_win_task_schedule.assert_not_called()

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
        url = f"{base_url}/{task.id}/run/"
        resp = self.client.post(url, format="json")
        self.assertEqual(resp.status_code, 200)
        run_win_task.assert_called()

        self.check_not_authenticated("post", url)


class TestAutoTaskCeleryTasks(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("agents.models.Agent.nats_cmd")
    def test_run_win_task(self, nats_cmd):
        self.agent = baker.make_recipe("agents.agent")
        self.task1 = AutomatedTask.objects.create(
            agent=self.agent,
            name="test task 1",
        )
        nats_cmd.return_value = "ok"
        ret = run_win_task.s(self.task1.pk).apply()
        self.assertEqual(ret.status, "SUCCESS")

    @patch("agents.models.Agent.nats_cmd")
    def test_create_win_task_schedule(self, nats_cmd):
        agent = baker.make_recipe("agents.agent", time_zone="UTC")

        # test daily task
        task1 = baker.make(
            "autotasks.AutomatedTask",
            agent=agent,
            name="test task 1",
            task_type=TaskType.DAILY,
            daily_interval=1,
            run_time_date=djangotime.now() + djangotime.timedelta(hours=3, minutes=30),
        )
        self.assertFalse(TaskResult.objects.filter(agent=agent, task=task1).exists())

        nats_cmd.return_value = "ok"
        create_win_task_schedule(pk=task1.pk)
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "pk": task1.pk,
                    "type": "rmm",
                    "name": task1.win_task_name,
                    "overwrite_task": True,
                    "enabled": True,
                    "trigger": "daily",
                    "multiple_instances": 1,
                    "delete_expired_task_after": False,
                    "start_when_available": False,
                    "start_year": int(task1.run_time_date.strftime("%Y")),
                    "start_month": int(task1.run_time_date.strftime("%-m")),
                    "start_day": int(task1.run_time_date.strftime("%-d")),
                    "start_hour": int(task1.run_time_date.strftime("%-H")),
                    "start_min": int(task1.run_time_date.strftime("%-M")),
                    "day_interval": 1,
                },
            },
            timeout=10,
        )
        nats_cmd.reset_mock()
        self.assertEqual(
            TaskResult.objects.get(task=task1, agent=agent).sync_status,
            TaskSyncStatus.SYNCED,
        )

        nats_cmd.return_value = "timeout"
        create_win_task_schedule(pk=task1.pk)
        self.assertEqual(
            TaskResult.objects.get(task=task1, agent=agent).sync_status,
            TaskSyncStatus.INITIAL,
        )
        nats_cmd.reset_mock()

        # test weekly task
        task1 = baker.make(
            "autotasks.AutomatedTask",
            agent=agent,
            name="test task 1",
            task_type=TaskType.WEEKLY,
            weekly_interval=1,
            run_asap_after_missed=True,
            run_time_bit_weekdays=127,
            run_time_date=djangotime.now() + djangotime.timedelta(hours=3, minutes=30),
            expire_date=djangotime.now() + djangotime.timedelta(days=100),
            task_instance_policy=2,
        )

        nats_cmd.return_value = "ok"
        create_win_task_schedule(pk=task1.pk)
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "pk": task1.pk,
                    "type": "rmm",
                    "name": task1.win_task_name,
                    "overwrite_task": True,
                    "enabled": True,
                    "trigger": "weekly",
                    "multiple_instances": 2,
                    "delete_expired_task_after": False,
                    "start_when_available": True,
                    "start_year": int(task1.run_time_date.strftime("%Y")),
                    "start_month": int(task1.run_time_date.strftime("%-m")),
                    "start_day": int(task1.run_time_date.strftime("%-d")),
                    "start_hour": int(task1.run_time_date.strftime("%-H")),
                    "start_min": int(task1.run_time_date.strftime("%-M")),
                    "expire_year": int(task1.expire_date.strftime("%Y")),
                    "expire_month": int(task1.expire_date.strftime("%-m")),
                    "expire_day": int(task1.expire_date.strftime("%-d")),
                    "expire_hour": int(task1.expire_date.strftime("%-H")),
                    "expire_min": int(task1.expire_date.strftime("%-M")),
                    "week_interval": 1,
                    "days_of_week": 127,
                },
            },
            timeout=10,
        )
        nats_cmd.reset_mock()

        # test monthly task
        task1 = baker.make(
            "autotasks.AutomatedTask",
            agent=agent,
            name="test task 1",
            task_type=TaskType.MONTHLY,
            random_task_delay="3M",
            task_repetition_interval="15M",
            task_repetition_duration="1D",
            stop_task_at_duration_end=True,
            monthly_days_of_month=0x80000030,
            monthly_months_of_year=0x400,
            run_time_date=djangotime.now() + djangotime.timedelta(hours=3, minutes=30),
        )

        nats_cmd.return_value = "ok"
        create_win_task_schedule(pk=task1.pk)
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "pk": task1.pk,
                    "type": "rmm",
                    "name": task1.win_task_name,
                    "overwrite_task": True,
                    "enabled": True,
                    "trigger": "monthly",
                    "multiple_instances": 1,
                    "delete_expired_task_after": False,
                    "start_when_available": False,
                    "start_year": int(task1.run_time_date.strftime("%Y")),
                    "start_month": int(task1.run_time_date.strftime("%-m")),
                    "start_day": int(task1.run_time_date.strftime("%-d")),
                    "start_hour": int(task1.run_time_date.strftime("%-H")),
                    "start_min": int(task1.run_time_date.strftime("%-M")),
                    "random_delay": "PT3M",
                    "repetition_interval": "PT15M",
                    "repetition_duration": "P1DT",
                    "stop_at_duration_end": True,
                    "days_of_month": 0x30,
                    "run_on_last_day_of_month": True,
                    "months_of_year": 1024,
                },
            },
            timeout=10,
        )
        nats_cmd.reset_mock()

        # test monthly dow
        task1 = baker.make(
            "autotasks.AutomatedTask",
            agent=agent,
            name="test task 1",
            task_type=TaskType.MONTHLY_DOW,
            run_time_bit_weekdays=56,
            monthly_months_of_year=0x400,
            monthly_weeks_of_month=3,
            run_time_date=djangotime.now() + djangotime.timedelta(hours=3, minutes=30),
        )
        nats_cmd.return_value = "ok"
        create_win_task_schedule(pk=task1.pk)
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "pk": task1.pk,
                    "type": "rmm",
                    "name": task1.win_task_name,
                    "overwrite_task": True,
                    "enabled": True,
                    "trigger": "monthlydow",
                    "multiple_instances": 1,
                    "delete_expired_task_after": False,
                    "start_when_available": False,
                    "start_year": int(task1.run_time_date.strftime("%Y")),
                    "start_month": int(task1.run_time_date.strftime("%-m")),
                    "start_day": int(task1.run_time_date.strftime("%-d")),
                    "start_hour": int(task1.run_time_date.strftime("%-H")),
                    "start_min": int(task1.run_time_date.strftime("%-M")),
                    "days_of_week": 56,
                    "months_of_year": 0x400,
                    "weeks_of_month": 3,
                },
            },
            timeout=10,
        )
        nats_cmd.reset_mock()

        # test runonce with future date
        task1 = baker.make(
            "autotasks.AutomatedTask",
            agent=agent,
            name="test task 2",
            task_type=TaskType.RUN_ONCE,
            run_time_date=djangotime.now() + djangotime.timedelta(hours=22),
            run_asap_after_missed=True,
        )
        nats_cmd.return_value = "ok"
        create_win_task_schedule(pk=task1.pk)
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "pk": task1.pk,
                    "type": "rmm",
                    "name": task1.win_task_name,
                    "overwrite_task": True,
                    "enabled": True,
                    "trigger": "runonce",
                    "multiple_instances": 1,
                    "delete_expired_task_after": False,
                    "start_when_available": True,
                    "start_year": int(task1.run_time_date.strftime("%Y")),
                    "start_month": int(task1.run_time_date.strftime("%-m")),
                    "start_day": int(task1.run_time_date.strftime("%-d")),
                    "start_hour": int(task1.run_time_date.strftime("%-H")),
                    "start_min": int(task1.run_time_date.strftime("%-M")),
                },
            },
            timeout=10,
        )
        nats_cmd.reset_mock()

        # test checkfailure task
        nats_cmd.reset_mock()
        check = baker.make_recipe("checks.diskspace_check", agent=agent)
        task1 = baker.make(
            "autotasks.AutomatedTask",
            agent=agent,
            name="test task 4",
            task_type=TaskType.CHECK_FAILURE,
            assigned_check=check,
        )
        nats_cmd.return_value = "ok"
        create_win_task_schedule(pk=task1.pk)
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "pk": task1.pk,
                    "type": "rmm",
                    "name": task1.win_task_name,
                    "overwrite_task": True,
                    "enabled": True,
                    "trigger": "manual",
                    "multiple_instances": 1,
                    "delete_expired_task_after": False,
                    "start_when_available": False,
                },
            },
            timeout=10,
        )
        nats_cmd.reset_mock()

        # test manual
        task1 = AutomatedTask.objects.create(
            agent=agent,
            name="test task 5",
            task_type=TaskType.MANUAL,
        )
        nats_cmd.return_value = "ok"
        create_win_task_schedule(pk=task1.pk)
        nats_cmd.assert_called_with(
            {
                "func": "schedtask",
                "schedtaskpayload": {
                    "pk": task1.pk,
                    "type": "rmm",
                    "name": task1.win_task_name,
                    "overwrite_task": True,
                    "enabled": True,
                    "trigger": "manual",
                    "multiple_instances": 1,
                    "delete_expired_task_after": False,
                    "start_when_available": False,
                },
            },
            timeout=10,
        )


class TestTaskPermissions(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.setup_client()

    def test_get_tasks_permissions(self):
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        unauthorized_agent = baker.make_recipe("agents.agent")
        task = baker.make("autotasks.AutomatedTask", agent=agent, _quantity=5)  # noqa
        unauthorized_task = baker.make(  # noqa
            "autotasks.AutomatedTask", agent=unauthorized_agent, _quantity=7
        )

        policy_tasks = baker.make(  # noqa
            "autotasks.AutomatedTask", policy=policy, _quantity=2
        )

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
        self.client.force_authenticate(user=user)

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
        self.assertEqual(len(r.data), 14)
        r = self.check_authorized("get", f"/agents/{agent.agent_id}/tasks/")
        self.assertEqual(len(r.data), 5)
        r = self.check_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/tasks/"
        )
        self.assertEqual(len(r.data), 7)
        r = self.check_authorized("get", f"/automation/policies/{policy.id}/tasks/")
        self.assertEqual(len(r.data), 2)

        # test limiting to client
        user.role.can_view_clients.set([agent.client])
        self.check_not_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/tasks/"
        )
        self.check_authorized("get", f"/agents/{agent.agent_id}/tasks/")
        self.check_authorized("get", f"/automation/policies/{policy.id}/tasks/")

        # make sure queryset is limited too
        r = self.client.get(f"{base_url}/")
        self.assertEqual(len(r.data), 7)

    def test_add_task_permissions(self):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        script = baker.make("scripts.Script")

        policy_data = {
            "policy": policy.id,
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

        for data in (policy_data, agent_data):
            # test superuser access
            self.check_authorized_superuser("post", url, data)

            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)

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

        for method in ("get", "put", "delete"):
            url = f"{base_url}/{task.id}/"
            unauthorized_url = f"{base_url}/{unauthorized_task.id}/"
            policy_url = f"{base_url}/{policy_task.id}/"

            # test superuser access
            self.check_authorized_superuser(method, url)
            self.check_authorized_superuser(method, unauthorized_url)
            self.check_authorized_superuser(method, policy_url)

            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)

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
        self.client.force_authenticate(user=user)

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
