from datetime import datetime, timedelta
from unittest.mock import patch

from django.conf import settings
from django.utils import timezone as djangotime
from model_bakery import baker, seq

from alerts.tasks import cache_agents_alert_template
from autotasks.models import AutomatedTask
from core.models import CoreSettings
from tacticalrmm.test import TacticalTestCase

from .models import Alert, AlertTemplate
from .serializers import (
    AlertSerializer,
    AlertTemplateRelationSerializer,
    AlertTemplateSerializer,
)


class TestAlertsViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_get_alerts(self):
        url = "/alerts/alerts/"

        # create check, task, and agent to test each serializer function
        check = baker.make_recipe("checks.diskspace_check")
        task = baker.make("autotasks.AutomatedTask")
        agent = baker.make_recipe("agents.agent")
        # setup data
        alerts = baker.make(
            "alerts.Alert",
            agent=agent,
            alert_time=seq(datetime.now(), timedelta(days=15)),
            severity="warning",
            _quantity=3,
        )
        baker.make(
            "alerts.Alert",
            assigned_check=check,
            alert_time=seq(datetime.now(), timedelta(days=15)),
            severity="error",
            _quantity=7,
        )
        baker.make(
            "alerts.Alert",
            assigned_task=task,
            snoozed=True,
            snooze_until=djangotime.now(),
            alert_time=seq(datetime.now(), timedelta(days=15)),
            _quantity=2,
        )
        baker.make(
            "alerts.Alert",
            agent=agent,
            resolved=True,
            resolved_on=djangotime.now(),
            alert_time=seq(datetime.now(), timedelta(days=15)),
            _quantity=9,
        )

        # test top alerts for alerts icon
        data = {"top": 3}
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEquals(resp.data["alerts"], AlertSerializer(alerts, many=True).data)  # type: ignore
        self.assertEquals(resp.data["alerts_count"], 10)  # type: ignore

        # test filter data
        # test data and result counts
        data = [
            {
                "filter": {
                    "timeFilter": 30,
                    "snoozedFilter": True,
                    "resolvedFilter": False,
                },
                "count": 12,
            },
            {
                "filter": {
                    "timeFilter": 45,
                    "snoozedFilter": False,
                    "resolvedFilter": False,
                },
                "count": 10,
            },
            {
                "filter": {
                    "severityFilter": ["error"],
                    "snoozedFilter": False,
                    "resolvedFilter": True,
                    "timeFilter": 20,
                },
                "count": 7,
            },
            {
                "filter": {
                    "clientFilter": [],
                    "snoozedFilter": True,
                    "resolvedFilter": False,
                },
                "count": 0,
            },
            {"filter": {}, "count": 21},
            {"filter": {"snoozedFilter": True, "resolvedFilter": False}, "count": 12},
        ]

        for req in data:
            resp = self.client.patch(url, req["filter"], format="json")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(resp.data), req["count"])  # type: ignore

        self.check_not_authenticated("patch", url)

    def test_add_alert(self):
        url = "/alerts/alerts/"

        agent = baker.make_recipe("agents.agent")
        data = {
            "alert_time": datetime.now(),
            "agent": agent.id,
            "severity": "warning",
            "alert_type": "availability",
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("post", url)

    def test_get_alert(self):
        # returns 404 for invalid alert pk
        resp = self.client.get("/alerts/alerts/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        alert = baker.make("alerts.Alert")
        url = f"/alerts/alerts/{alert.pk}/"  # type: ignore

        resp = self.client.get(url, format="json")
        serializer = AlertSerializer(alert)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_update_alert(self):
        # returns 404 for invalid alert pk
        resp = self.client.put("/alerts/alerts/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        alert = baker.make("alerts.Alert", resolved=False, snoozed=False)

        url = f"/alerts/alerts/{alert.pk}/"  # type: ignore

        # test resolving alert
        data = {
            "id": alert.pk,  # type: ignore
            "type": "resolve",
        }
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Alert.objects.get(pk=alert.pk).resolved)  # type: ignore
        self.assertTrue(Alert.objects.get(pk=alert.pk).resolved_on)  # type: ignore

        # test snoozing alert
        data = {"id": alert.pk, "type": "snooze", "snooze_days": "30"}  # type: ignore
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Alert.objects.get(pk=alert.pk).snoozed)  # type: ignore
        self.assertTrue(Alert.objects.get(pk=alert.pk).snooze_until)  # type: ignore

        # test snoozing alert without snooze_days
        data = {"id": alert.pk, "type": "snooze"}  # type: ignore
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        # test unsnoozing alert
        data = {"id": alert.pk, "type": "unsnooze"}  # type: ignore
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Alert.objects.get(pk=alert.pk).snoozed)  # type: ignore
        self.assertFalse(Alert.objects.get(pk=alert.pk).snooze_until)  # type: ignore

        # test invalid type
        data = {"id": alert.pk, "type": "invalid"}  # type: ignore
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("put", url)

    def test_delete_alert(self):
        # returns 404 for invalid alert pk
        resp = self.client.put("/alerts/alerts/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        alert = baker.make("alerts.Alert")

        # test delete alert
        url = f"/alerts/alerts/{alert.pk}/"  # type: ignore
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        self.assertFalse(Alert.objects.filter(pk=alert.pk).exists())  # type: ignore
        self.check_not_authenticated("delete", url)

    def test_bulk_alert_actions(self):
        url = "/alerts/bulk/"

        # setup data
        alerts = baker.make("alerts.Alert", resolved=False, _quantity=3)

        # test invalid data
        data = {"bulk_action": "invalid"}
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        # test snooze without snooze days
        data = {"bulk_action": "snooze"}
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        # test bulk snoozing alerts
        data = {
            "bulk_action": "snooze",
            "alerts": [alert.pk for alert in alerts],  # type: ignore
            "snooze_days": "30",
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Alert.objects.filter(snoozed=False).exists())

        # test bulk resolving alerts
        data = {"bulk_action": "resolve", "alerts": [alert.pk for alert in alerts]}  # type: ignore

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Alert.objects.filter(resolved=False).exists())
        self.assertTrue(Alert.objects.filter(snoozed=False).exists())

    def test_get_alert_templates(self):
        url = "/alerts/alerttemplates/"

        alert_templates = baker.make("alerts.AlertTemplate", _quantity=3)
        resp = self.client.get(url, format="json")
        serializer = AlertTemplateSerializer(alert_templates, many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_add_alert_template(self):
        url = "/alerts/alerttemplates/"

        data = {
            "name": "Test Template",
        }

        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("post", url)

    def test_get_alert_template(self):
        # returns 404 for invalid alert template pk
        resp = self.client.get("/alerts/alerttemplates/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        alert_template = baker.make("alerts.AlertTemplate")
        url = f"/alerts/alerttemplates/{alert_template.pk}/"  # type: ignore

        resp = self.client.get(url, format="json")
        serializer = AlertTemplateSerializer(alert_template)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore

        self.check_not_authenticated("get", url)

    def test_update_alert_template(self):
        # returns 404 for invalid alert pk
        resp = self.client.put("/alerts/alerttemplates/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        alert_template = baker.make("alerts.AlertTemplate")

        url = f"/alerts/alerttemplates/{alert_template.pk}/"  # type: ignore

        # test data
        data = {
            "id": alert_template.pk,  # type: ignore
            "agent_email_on_resolved": True,
            "agent_text_on_resolved": True,
            "agent_include_desktops": True,
            "agent_always_email": True,
            "agent_always_text": True,
            "agent_always_alert": True,
            "agent_periodic_alert_days": "90",
        }
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("put", url)

    def test_delete_alert_template(self):
        # returns 404 for invalid alert pk
        resp = self.client.put("/alerts/alerttemplates/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        alert_template = baker.make("alerts.AlertTemplate")

        # test delete alert
        url = f"/alerts/alerttemplates/{alert_template.pk}/"  # type: ignore
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        self.assertFalse(AlertTemplate.objects.filter(pk=alert_template.pk).exists())  # type: ignore

        self.check_not_authenticated("delete", url)

    def test_alert_template_related(self):
        # setup data
        alert_template = baker.make("alerts.AlertTemplate")
        baker.make("clients.Client", alert_template=alert_template, _quantity=2)
        baker.make("clients.Site", alert_template=alert_template, _quantity=3)
        baker.make("automation.Policy", alert_template=alert_template)
        core = CoreSettings.objects.first()
        core.alert_template = alert_template
        core.save()

        url = f"/alerts/alerttemplates/{alert_template.pk}/related/"  # type: ignore

        resp = self.client.get(url, format="json")
        serializer = AlertTemplateRelationSerializer(alert_template)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore
        self.assertEqual(len(resp.data["policies"]), 1)  # type: ignore
        self.assertEqual(len(resp.data["clients"]), 2)  # type: ignore
        self.assertEqual(len(resp.data["sites"]), 3)  # type: ignore
        self.assertTrue(
            AlertTemplate.objects.get(pk=alert_template.pk).is_default_template  # type: ignore
        )


class TestAlertTasks(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_unsnooze_alert_task(self):
        from alerts.tasks import unsnooze_alerts

        # these will be unsnoozed whent eh function is run
        not_snoozed = baker.make(
            "alerts.Alert",
            snoozed=True,
            snooze_until=seq(datetime.now(), timedelta(days=15)),
            _quantity=5,
        )

        # these will still be snoozed after the function is run
        snoozed = baker.make(
            "alerts.Alert",
            snoozed=True,
            snooze_until=seq(datetime.now(), timedelta(days=-15)),
            _quantity=5,
        )

        unsnooze_alerts()

        self.assertFalse(
            Alert.objects.filter(
                pk__in=[alert.pk for alert in not_snoozed], snoozed=False  # type: ignore
            ).exists()
        )
        self.assertTrue(
            Alert.objects.filter(
                pk__in=[alert.pk for alert in snoozed], snoozed=False  # type: ignore
            ).exists()
        )

    def test_agent_gets_correct_alert_template(self):

        core = CoreSettings.objects.first()
        # setup data
        workstation = baker.make_recipe("agents.agent", monitoring_type="workstation")
        server = baker.make_recipe("agents.agent", monitoring_type="server")

        policy = baker.make("automation.Policy", active=True)

        alert_templates = baker.make("alerts.AlertTemplate", _quantity=6)

        # should be None
        self.assertFalse(workstation.set_alert_template())
        self.assertFalse(server.set_alert_template())

        # assign first Alert Template as to a policy and apply it as default
        policy.alert_template = alert_templates[0]  # type: ignore
        policy.save()  # type: ignore
        core.workstation_policy = policy
        core.server_policy = policy
        core.save()

        self.assertEquals(server.set_alert_template().pk, alert_templates[0].pk)  # type: ignore
        self.assertEquals(workstation.set_alert_template().pk, alert_templates[0].pk)  # type: ignore

        # assign second Alert Template to as default alert template
        core.alert_template = alert_templates[1]  # type: ignore
        core.save()

        self.assertEquals(workstation.set_alert_template().pk, alert_templates[1].pk)  # type: ignore
        self.assertEquals(server.set_alert_template().pk, alert_templates[1].pk)  # type: ignore

        # assign third Alert Template to client
        workstation.client.alert_template = alert_templates[2]  # type: ignore
        server.client.alert_template = alert_templates[2]  # type: ignore
        workstation.client.save()
        server.client.save()

        self.assertEquals(workstation.set_alert_template().pk, alert_templates[2].pk)  # type: ignore
        self.assertEquals(server.set_alert_template().pk, alert_templates[2].pk)  # type: ignore

        # apply policy to client and should override
        workstation.client.workstation_policy = policy
        server.client.server_policy = policy
        workstation.client.save()
        server.client.save()

        self.assertEquals(workstation.set_alert_template().pk, alert_templates[0].pk)  # type: ignore
        self.assertEquals(server.set_alert_template().pk, alert_templates[0].pk)  # type: ignore

        # assign fouth Alert Template to site
        workstation.site.alert_template = alert_templates[3]  # type: ignore
        server.site.alert_template = alert_templates[3]  # type: ignore
        workstation.site.save()
        server.site.save()

        self.assertEquals(workstation.set_alert_template().pk, alert_templates[3].pk)  # type: ignore
        self.assertEquals(server.set_alert_template().pk, alert_templates[3].pk)  # type: ignore

        # apply policy to site
        workstation.site.workstation_policy = policy
        server.site.server_policy = policy
        workstation.site.save()
        server.site.save()

        self.assertEquals(workstation.set_alert_template().pk, alert_templates[0].pk)  # type: ignore
        self.assertEquals(server.set_alert_template().pk, alert_templates[0].pk)  # type: ignore

        # apply policy to agents
        workstation.policy = policy
        server.policy = policy
        workstation.save()
        server.save()

        self.assertEquals(workstation.set_alert_template().pk, alert_templates[0].pk)  # type: ignore
        self.assertEquals(server.set_alert_template().pk, alert_templates[0].pk)  # type: ignore

        # test disabling alert template
        alert_templates[0].is_active = False  # type: ignore
        alert_templates[0].save()  # type: ignore

        self.assertEquals(workstation.set_alert_template().pk, alert_templates[3].pk)  # type: ignore
        self.assertEquals(server.set_alert_template().pk, alert_templates[3].pk)  # type: ignore

        # test policy exclusions
        alert_templates[3].excluded_agents.set([workstation.pk])  # type: ignore

        self.assertEquals(workstation.set_alert_template().pk, alert_templates[2].pk)  # type: ignore
        self.assertEquals(server.set_alert_template().pk, alert_templates[3].pk)  # type: ignore

        # test workstation exclusions
        alert_templates[2].exclude_workstations = True  # type: ignore
        alert_templates[2].save()  # type: ignore

        self.assertEquals(workstation.set_alert_template().pk, alert_templates[1].pk)  # type: ignore
        self.assertEquals(server.set_alert_template().pk, alert_templates[3].pk)  # type: ignore

        # test server exclusions
        alert_templates[3].exclude_servers = True  # type: ignore
        alert_templates[3].save()  # type: ignore

        self.assertEquals(workstation.set_alert_template().pk, alert_templates[1].pk)  # type: ignore
        self.assertEquals(server.set_alert_template().pk, alert_templates[2].pk)  # type: ignore

    @patch("agents.tasks.sleep")
    @patch("core.models.CoreSettings.send_mail")
    @patch("core.models.CoreSettings.send_sms")
    @patch("agents.tasks.agent_outage_sms_task.delay")
    @patch("agents.tasks.agent_outage_email_task.delay")
    @patch("agents.tasks.agent_recovery_email_task.delay")
    @patch("agents.tasks.agent_recovery_sms_task.delay")
    def test_handle_agent_alerts(
        self,
        recovery_sms,
        recovery_email,
        outage_email,
        outage_sms,
        send_sms,
        send_email,
        sleep,
    ):
        from agents.models import Agent
        from agents.tasks import (
            agent_outage_email_task,
            agent_outage_sms_task,
            agent_outages_task,
            agent_recovery_email_task,
            agent_recovery_sms_task,
        )
        from alerts.models import Alert

        agent_dashboard_alert = baker.make_recipe("agents.overdue_agent")

        # call outages task and no alert should be created
        agent_outages_task()

        self.assertEquals(Alert.objects.count(), 0)

        # set overdue_dashboard_alert and alert should be created
        agent_dashboard_alert.overdue_dashboard_alert = True
        agent_dashboard_alert.save()

        # create other agents with various alert settings
        alert_template_always_alert = baker.make(
            "alerts.AlertTemplate", is_active=True, agent_always_alert=True
        )
        alert_template_always_text = baker.make(
            "alerts.AlertTemplate",
            is_active=True,
            agent_always_text=True,
            agent_periodic_alert_days=5,
        )
        alert_template_always_email = baker.make(
            "alerts.AlertTemplate",
            is_active=True,
            agent_always_email=True,
            agent_periodic_alert_days=5,
        )

        alert_template_blank = baker.make("alerts.AlertTemplate", is_active=True)

        agent_template_email = baker.make_recipe("agents.overdue_agent")
        agent_template_dashboard = baker.make_recipe("agents.overdue_agent")
        agent_template_text = baker.make_recipe("agents.overdue_agent")
        agent_template_blank = baker.make_recipe("agents.overdue_agent")

        # assign alert templates to agent's clients
        agent_template_email.client.alert_template = alert_template_always_email
        agent_template_email.client.save()
        agent_template_dashboard.client.alert_template = alert_template_always_alert
        agent_template_dashboard.client.save()
        agent_template_text.client.alert_template = alert_template_always_text
        agent_template_text.client.save()
        agent_template_blank.client.alert_template = alert_template_blank
        agent_template_blank.client.save()

        agent_text_alert = baker.make_recipe(
            "agents.overdue_agent", overdue_text_alert=True
        )
        agent_email_alert = baker.make_recipe(
            "agents.overdue_agent", overdue_email_alert=True
        )

        cache_agents_alert_template()
        agent_outages_task()

        # should have created 6 alerts
        self.assertEquals(Alert.objects.count(), 6)

        # other specific agents should have created alerts
        self.assertEquals(Alert.objects.filter(agent=agent_dashboard_alert).count(), 1)
        self.assertEquals(Alert.objects.filter(agent=agent_text_alert).count(), 1)
        self.assertEquals(Alert.objects.filter(agent=agent_email_alert).count(), 1)
        self.assertEquals(Alert.objects.filter(agent=agent_template_email).count(), 1)
        self.assertEquals(
            Alert.objects.filter(agent=agent_template_dashboard).count(), 1
        )
        self.assertEquals(Alert.objects.filter(agent=agent_template_text).count(), 1)
        self.assertEquals(Alert.objects.filter(agent=agent_template_blank).count(), 0)

        # check if email and text tasks were called
        self.assertEquals(outage_email.call_count, 2)
        self.assertEquals(outage_sms.call_count, 2)

        outage_sms.assert_any_call(
            pk=Alert.objects.get(agent=agent_text_alert).pk, alert_interval=None
        )
        outage_sms.assert_any_call(
            pk=Alert.objects.get(agent=agent_template_text).pk, alert_interval=5
        )
        outage_email.assert_any_call(
            pk=Alert.objects.get(agent=agent_email_alert).pk, alert_interval=None
        )
        outage_email.assert_any_call(
            pk=Alert.objects.get(agent=agent_template_email).pk, alert_interval=5
        )

        # call the email/sms outage tasks synchronously
        agent_outage_sms_task(
            pk=Alert.objects.get(agent=agent_text_alert).pk, alert_interval=None
        )
        agent_outage_email_task(
            pk=Alert.objects.get(agent=agent_email_alert).pk, alert_interval=None
        )
        agent_outage_sms_task(
            pk=Alert.objects.get(agent=agent_template_text).pk, alert_interval=5
        )
        agent_outage_email_task(
            pk=Alert.objects.get(agent=agent_template_email).pk, alert_interval=5
        )

        # check if email/text sent was set
        self.assertTrue(Alert.objects.get(agent=agent_text_alert).sms_sent)
        self.assertFalse(Alert.objects.get(agent=agent_text_alert).email_sent)
        self.assertTrue(Alert.objects.get(agent=agent_email_alert).email_sent)
        self.assertFalse(Alert.objects.get(agent=agent_email_alert).sms_sent)
        self.assertTrue(Alert.objects.get(agent=agent_template_text).sms_sent)
        self.assertTrue(Alert.objects.get(agent=agent_template_email).email_sent)
        self.assertFalse(Alert.objects.get(agent=agent_dashboard_alert).email_sent)
        self.assertFalse(Alert.objects.get(agent=agent_dashboard_alert).sms_sent)

        # calling agent outage task again shouldn't create duplicate alerts and won't send alerts
        agent_outages_task()
        self.assertEquals(Alert.objects.count(), 6)

        # test periodic notification
        # change email/text sent to sometime in the past
        alert_text = Alert.objects.get(agent=agent_template_text)
        alert_text.sms_sent = djangotime.now() - djangotime.timedelta(days=20)
        alert_text.save()
        alert_email = Alert.objects.get(agent=agent_template_email)
        alert_email.email_sent = djangotime.now() - djangotime.timedelta(days=20)
        alert_email.save()

        send_sms.reset_mock()
        send_email.reset_mock()

        agent_outages_task()

        outage_sms.assert_any_call(
            pk=Alert.objects.get(agent=agent_template_text).pk, alert_interval=5
        )
        outage_email.assert_any_call(
            pk=Alert.objects.get(agent=agent_template_email).pk, alert_interval=5
        )

        agent_outage_sms_task(
            pk=Alert.objects.get(agent=agent_template_text).pk, alert_interval=5
        )
        agent_outage_email_task(
            pk=Alert.objects.get(agent=agent_template_email).pk, alert_interval=5
        )

        self.assertEqual(send_sms.call_count, 1)
        self.assertEqual(send_email.call_count, 1)

        # test resolved alerts
        # alter the alert template to email and test on resolved
        alert_template_always_email.agent_email_on_resolved = True  # type: ignore
        alert_template_always_email.save()  # type: ignore
        alert_template_always_text.agent_text_on_resolved = True  # type: ignore
        alert_template_always_text.save()  # type: ignore

        agent_template_text = Agent.objects.get(pk=agent_template_text.pk)
        agent_template_email = Agent.objects.get(pk=agent_template_email.pk)

        # have the two agents checkin
        url = "/api/v3/checkin/"

        agent_template_text.version = settings.LATEST_AGENT_VER
        agent_template_text.save()
        agent_template_email.version = settings.LATEST_AGENT_VER
        agent_template_email.save()

        data = {
            "agent_id": agent_template_text.agent_id,
            "version": settings.LATEST_AGENT_VER,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        data = {
            "agent_id": agent_template_email.agent_id,
            "version": settings.LATEST_AGENT_VER,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        recovery_sms.assert_called_with(
            pk=Alert.objects.get(agent=agent_template_text).pk
        )
        recovery_email.assert_any_call(
            pk=Alert.objects.get(agent=agent_template_email).pk
        )

        agent_recovery_sms_task(pk=Alert.objects.get(agent=agent_template_text).pk)
        agent_recovery_email_task(pk=Alert.objects.get(agent=agent_template_email).pk)

        self.assertTrue(Alert.objects.get(agent=agent_template_text).resolved_sms_sent)
        self.assertTrue(
            Alert.objects.get(agent=agent_template_email).resolved_email_sent
        )

    @patch("checks.tasks.sleep")
    @patch("core.models.CoreSettings.send_mail")
    @patch("core.models.CoreSettings.send_sms")
    @patch("checks.tasks.handle_check_sms_alert_task.delay")
    @patch("checks.tasks.handle_check_email_alert_task.delay")
    @patch("checks.tasks.handle_resolved_check_email_alert_task.delay")
    @patch("checks.tasks.handle_resolved_check_sms_alert_task.delay")
    def test_handle_check_alerts(
        self,
        resolved_sms,
        resolved_email,
        outage_email,
        outage_sms,
        send_sms,
        send_email,
        sleep,
    ):
        from alerts.tasks import cache_agents_alert_template
        from checks.models import Check
        from checks.tasks import (
            handle_check_email_alert_task,
            handle_check_sms_alert_task,
            handle_resolved_check_email_alert_task,
            handle_resolved_check_sms_alert_task,
        )

        # create test data
        agent = baker.make_recipe("agents.agent")
        agent_no_settings = baker.make_recipe("agents.agent")
        agent_template_email = baker.make_recipe("agents.agent")
        agent_template_dashboard_text = baker.make_recipe("agents.agent")
        agent_template_blank = baker.make_recipe("agents.agent")

        # add disks to diskspace check agent
        agent.disks = [
            {
                "free": "64.7G",
                "used": "167.6G",
                "total": "232.3G",
                "device": "C:",
                "fstype": "NTFS",
                "percent": 72,
            }
        ]
        agent.save()

        # create agent with template to always email on warning severity
        alert_template_email = baker.make(
            "alerts.AlertTemplate",
            is_active=True,
            check_always_email=True,
            check_email_alert_severity=["warning"],
        )
        agent_template_email.client.alert_template = alert_template_email
        agent_template_email.client.save()

        # create agent with template to always dashboard and text on various alert severities
        alert_template_dashboard_text = baker.make(
            "alerts.AlertTemplate",
            is_active=True,
            check_always_alert=True,
            check_always_text=True,
            check_dashboard_alert_severity=["info", "warning", "error"],
            check_text_alert_severity=["error"],
        )
        agent_template_dashboard_text.client.alert_template = (
            alert_template_dashboard_text
        )
        agent_template_dashboard_text.client.save()

        # create agent with blank template
        alert_template_blank = baker.make("alerts.AlertTemplate", is_active=True)
        agent_template_blank.client.alert_template = alert_template_blank
        agent_template_blank.client.save()

        # create some checks per agent above
        check_agent = baker.make_recipe(
            "checks.diskspace_check",
            agent=agent,
            email_alert=True,
            text_alert=True,
            dashboard_alert=True,
            alert_severity="warning",
        )
        check_template_email = baker.make_recipe(
            "checks.cpuload_check", agent=agent_template_email, history=[50, 40, 30]
        )
        check_template_dashboard_text = baker.make_recipe(
            "checks.memory_check",
            agent=agent_template_dashboard_text,
            history=[50, 40, 30],
        )
        check_template_blank = baker.make_recipe(
            "checks.ping_check", agent=agent_template_blank
        )
        check_no_settings = baker.make_recipe(
            "checks.script_check", agent=agent_no_settings
        )

        # update alert template and pull new checks from DB
        cache_agents_alert_template()
        check_template_email = Check.objects.get(pk=check_template_email.pk)
        check_template_dashboard_text = Check.objects.get(
            pk=check_template_dashboard_text.pk
        )
        check_template_blank = Check.objects.get(pk=check_template_blank.pk)

        # test agent with check that has alert settings
        check_agent.alert_severity = "warning"
        check_agent.status = "failing"

        Alert.handle_alert_failure(check_agent)

        # alert should have been created and sms, email notifications sent
        self.assertTrue(Alert.objects.filter(assigned_check=check_agent).exists())
        alertpk = Alert.objects.get(assigned_check=check_agent).pk
        outage_sms.assert_called_with(pk=alertpk, alert_interval=None)
        outage_email.assert_called_with(pk=alertpk, alert_interval=None)
        outage_sms.reset_mock()
        outage_email.reset_mock()

        # call outage email/sms tasks synchronously
        handle_check_sms_alert_task(pk=alertpk, alert_interval=None)
        handle_check_email_alert_task(pk=alertpk, alert_interval=None)

        alert = Alert.objects.get(assigned_check=check_agent)
        # make sure the email/text sent fields were set
        self.assertTrue(alert.email_sent)
        self.assertTrue(alert.sms_sent)

        # make sure the dashboard alert will be visible since dashboard_alert is enabled
        self.assertFalse(alert.hidden)

        send_email.assert_called()
        send_sms.assert_called()
        send_email.reset_mock()
        send_sms.reset_mock()

        # test check with an agent that has an email always alert template
        Alert.handle_alert_failure(check_template_email)

        self.assertTrue(Alert.objects.filter(assigned_check=check_template_email))
        alertpk = Alert.objects.get(assigned_check=check_template_email).pk
        outage_sms.assert_not_called()
        outage_email.assert_called_with(pk=alertpk, alert_interval=0)
        outage_email.reset_mock()

        # call outage email task synchronously
        handle_check_email_alert_task(pk=alertpk, alert_interval=0)

        # make sure dashboard alert is hidden
        self.assertTrue(Alert.objects.get(assigned_check=check_template_email).hidden)

        send_email.assert_called()
        send_email.reset_mock()

        # test check with an agent that has an email always alert template
        Alert.handle_alert_failure(check_template_dashboard_text)

        self.assertTrue(
            Alert.objects.filter(assigned_check=check_template_dashboard_text).exists()
        )
        alertpk = Alert.objects.get(assigned_check=check_template_dashboard_text).pk

        # should only trigger when alert with severity of error
        outage_sms.assert_not_called

        # update check alert seveity to error
        check_template_dashboard_text.alert_severity = "error"
        check_template_dashboard_text.save()

        # now should trigger alert
        Alert.handle_alert_failure(check_template_dashboard_text)
        outage_sms.assert_called_with(pk=alertpk, alert_interval=0)
        outage_sms.reset_mock()

        # call outage email task synchronously
        handle_check_sms_alert_task(pk=alertpk, alert_interval=0)

        # make sure dashboard alert is not hidden
        self.assertFalse(
            Alert.objects.get(assigned_check=check_template_dashboard_text).hidden
        )

        send_sms.assert_called()
        send_sms.reset_mock()

        # test check with an agent that has a blank alert template
        Alert.handle_alert_failure(check_template_blank)

        self.assertFalse(
            Alert.objects.filter(assigned_check=check_template_blank).exists()
        )

        # test check that has no template and no settings
        Alert.handle_alert_failure(check_no_settings)

        self.assertFalse(
            Alert.objects.filter(assigned_check=check_no_settings).exists()
        )

        # test periodic notifications

        # make sure a failing check won't trigger another notification and only create a single alert
        Alert.handle_alert_failure(check_template_email)
        send_email.assert_not_called()
        send_sms.assert_not_called()

        self.assertEquals(
            Alert.objects.filter(assigned_check=check_template_email).count(), 1
        )

        alert_template_email.check_periodic_alert_days = 1  # type: ignore
        alert_template_email.save()  # type: ignore

        alert_template_dashboard_text.check_periodic_alert_days = 1  # type: ignore
        alert_template_dashboard_text.save()  # type: ignore

        # set last email time for alert in the past
        alert_email = Alert.objects.get(assigned_check=check_template_email)
        alert_email.email_sent = djangotime.now() - djangotime.timedelta(days=20)
        alert_email.save()

        # set last email time for alert in the past
        alert_sms = Alert.objects.get(assigned_check=check_template_dashboard_text)
        alert_sms.sms_sent = djangotime.now() - djangotime.timedelta(days=20)
        alert_sms.save()

        # refresh checks to get alert template changes
        check_template_email = Check.objects.get(pk=check_template_email.pk)
        check_template_dashboard_text = Check.objects.get(
            pk=check_template_dashboard_text.pk
        )
        check_template_blank = Check.objects.get(pk=check_template_blank.pk)

        Alert.handle_alert_failure(check_template_email)
        Alert.handle_alert_failure(check_template_dashboard_text)

        outage_email.assert_called_with(pk=alert_email.pk, alert_interval=1)
        outage_sms.assert_called_with(pk=alert_sms.pk, alert_interval=1)
        outage_email.reset_mock()
        outage_sms.reset_mock()

        # test resolving alerts
        Alert.handle_alert_resolve(check_agent)

        self.assertTrue(Alert.objects.get(assigned_check=check_agent).resolved)
        self.assertTrue(Alert.objects.get(assigned_check=check_agent).resolved_on)

        resolved_sms.assert_not_called()
        resolved_email.assert_not_called()

        # test resolved notifications
        alert_template_email.check_email_on_resolved = True  # type: ignore
        alert_template_email.save()  # type: ignore

        alert_template_dashboard_text.check_text_on_resolved = True  # type: ignore
        alert_template_dashboard_text.save()  # type: ignore

        # refresh checks to get alert template changes
        check_template_email = Check.objects.get(pk=check_template_email.pk)
        check_template_dashboard_text = Check.objects.get(
            pk=check_template_dashboard_text.pk
        )
        check_template_blank = Check.objects.get(pk=check_template_blank.pk)

        Alert.handle_alert_resolve(check_template_email)

        resolved_email.assert_called_with(pk=alert_email.pk)
        resolved_sms.assert_not_called()
        resolved_email.reset_mock()

        Alert.handle_alert_resolve(check_template_dashboard_text)

        resolved_sms.assert_called_with(pk=alert_sms.pk)
        resolved_email.assert_not_called()

        # call the email and sms tasks synchronously
        handle_resolved_check_sms_alert_task(pk=alert_sms.pk)
        handle_resolved_check_email_alert_task(pk=alert_email.pk)

        send_email.assert_called()
        send_sms.assert_called()

    @patch("autotasks.tasks.sleep")
    @patch("core.models.CoreSettings.send_mail")
    @patch("core.models.CoreSettings.send_sms")
    @patch("autotasks.tasks.handle_task_sms_alert.delay")
    @patch("autotasks.tasks.handle_task_email_alert.delay")
    @patch("autotasks.tasks.handle_resolved_task_email_alert.delay")
    @patch("autotasks.tasks.handle_resolved_task_sms_alert.delay")
    def test_handle_task_alerts(
        self,
        resolved_sms,
        resolved_email,
        outage_email,
        outage_sms,
        send_sms,
        send_email,
        sleep,
    ):
        from alerts.tasks import cache_agents_alert_template
        from autotasks.models import AutomatedTask
        from autotasks.tasks import (
            handle_resolved_task_email_alert,
            handle_resolved_task_sms_alert,
            handle_task_email_alert,
            handle_task_sms_alert,
        )

        # create test data
        agent = baker.make_recipe("agents.agent")
        agent_no_settings = baker.make_recipe("agents.agent")
        agent_template_email = baker.make_recipe("agents.agent")
        agent_template_dashboard_text = baker.make_recipe("agents.agent")
        agent_template_blank = baker.make_recipe("agents.agent")

        # create agent with template to always email on warning severity
        alert_template_email = baker.make(
            "alerts.AlertTemplate",
            is_active=True,
            task_always_email=True,
            task_email_alert_severity=["warning"],
        )
        agent_template_email.client.alert_template = alert_template_email
        agent_template_email.client.save()

        # create agent with template to always dashboard and text on various alert severities
        alert_template_dashboard_text = baker.make(
            "alerts.AlertTemplate",
            is_active=True,
            task_always_alert=True,
            task_always_text=True,
            task_dashboard_alert_severity=["info", "warning", "error"],
            task_text_alert_severity=["error"],
        )
        agent_template_dashboard_text.client.alert_template = (
            alert_template_dashboard_text
        )
        agent_template_dashboard_text.client.save()

        # create agent with blank template
        alert_template_blank = baker.make("alerts.AlertTemplate", is_active=True)
        agent_template_blank.client.alert_template = alert_template_blank
        agent_template_blank.client.save()

        # create some tasks per agent above
        task_agent = baker.make(
            "autotasks.AutomatedTask",
            agent=agent,
            email_alert=True,
            text_alert=True,
            dashboard_alert=True,
            alert_severity="warning",
        )
        task_template_email = baker.make(
            "autotasks.AutomatedTask",
            agent=agent_template_email,
            alert_severity="warning",
        )
        task_template_dashboard_text = baker.make(
            "autotasks.AutomatedTask",
            agent=agent_template_dashboard_text,
            alert_severity="info",
        )
        task_template_blank = baker.make(
            "autotasks.AutomatedTask",
            agent=agent_template_blank,
            alert_severity="error",
        )
        task_no_settings = baker.make(
            "autotasks.AutomatedTask", agent=agent_no_settings, alert_severity="warning"
        )

        # update alert template and pull new checks from DB
        cache_agents_alert_template()
        task_template_email = AutomatedTask.objects.get(pk=task_template_email.pk)  # type: ignore
        task_template_dashboard_text = AutomatedTask.objects.get(pk=task_template_dashboard_text.pk)  # type: ignore
        task_template_blank = AutomatedTask.objects.get(pk=task_template_blank.pk)  # type: ignore

        # test agent with task that has alert settings
        Alert.handle_alert_failure(task_agent)  # type: ignore

        # alert should have been created and sms, email notifications sent
        self.assertTrue(Alert.objects.filter(assigned_task=task_agent).exists())
        alertpk = Alert.objects.get(assigned_task=task_agent).pk
        outage_sms.assert_called_with(pk=alertpk, alert_interval=None)
        outage_email.assert_called_with(pk=alertpk, alert_interval=None)
        outage_sms.reset_mock()
        outage_email.reset_mock()

        # call outage email/sms tasks synchronously
        handle_task_sms_alert(pk=alertpk, alert_interval=None)
        handle_task_email_alert(pk=alertpk, alert_interval=None)

        alert = Alert.objects.get(assigned_task=task_agent)
        # make sure the email/text sent fields were set
        self.assertTrue(alert.email_sent)
        self.assertTrue(alert.sms_sent)

        # make sure the dashboard alert will be visible since dashboard_alert is enabled
        self.assertFalse(alert.hidden)

        send_email.assert_called()
        send_sms.assert_called()
        send_email.reset_mock()
        send_sms.reset_mock()

        # test task with an agent that has an email always alert template
        Alert.handle_alert_failure(task_template_email)  # type: ignore

        self.assertTrue(Alert.objects.filter(assigned_task=task_template_email))
        alertpk = Alert.objects.get(assigned_task=task_template_email).pk
        outage_sms.assert_not_called()
        outage_email.assert_called_with(pk=alertpk, alert_interval=0)
        outage_email.reset_mock()

        # call outage email task synchronously
        handle_task_email_alert(pk=alertpk, alert_interval=0)

        # make sure dashboard alert is hidden
        self.assertTrue(Alert.objects.get(assigned_task=task_template_email).hidden)

        send_email.assert_called()
        send_email.reset_mock()

        # test task with an agent that has an email always alert template
        Alert.handle_alert_failure(task_template_dashboard_text)  # type: ignore

        self.assertTrue(
            Alert.objects.filter(assigned_task=task_template_dashboard_text).exists()
        )
        alertpk = Alert.objects.get(assigned_task=task_template_dashboard_text).pk

        # should only trigger when alert with severity of error
        outage_sms.assert_not_called

        # update task alert seveity to error
        task_template_dashboard_text.alert_severity = "error"  # type: ignore
        task_template_dashboard_text.save()  # type: ignore

        # now should trigger alert
        Alert.handle_alert_failure(task_template_dashboard_text)  # type: ignore
        outage_sms.assert_called_with(pk=alertpk, alert_interval=0)
        outage_sms.reset_mock()

        # call outage email task synchronously
        handle_task_sms_alert(pk=alertpk, alert_interval=0)

        # make sure dashboard alert is not hidden
        self.assertFalse(
            Alert.objects.get(assigned_task=task_template_dashboard_text).hidden
        )

        send_sms.assert_called()
        send_sms.reset_mock()

        # test task with an agent that has a blank alert template
        Alert.handle_alert_failure(task_template_blank)  # type: ignore

        self.assertFalse(
            Alert.objects.filter(assigned_task=task_template_blank).exists()
        )

        # test task that has no template and no settings
        Alert.handle_alert_failure(task_no_settings)  # type: ignore

        self.assertFalse(Alert.objects.filter(assigned_task=task_no_settings).exists())

        # test periodic notifications

        # make sure a failing task won't trigger another notification and only create a single alert
        Alert.handle_alert_failure(task_template_email)  # type: ignore
        send_email.assert_not_called()
        send_sms.assert_not_called()

        self.assertEquals(
            Alert.objects.filter(assigned_task=task_template_email).count(), 1
        )

        alert_template_email.task_periodic_alert_days = 1  # type: ignore
        alert_template_email.save()  # type: ignore

        alert_template_dashboard_text.task_periodic_alert_days = 1  # type: ignore
        alert_template_dashboard_text.save()  # type: ignore

        # set last email time for alert in the past
        alert_email = Alert.objects.get(assigned_task=task_template_email)
        alert_email.email_sent = djangotime.now() - djangotime.timedelta(days=20)
        alert_email.save()

        # set last email time for alert in the past
        alert_sms = Alert.objects.get(assigned_task=task_template_dashboard_text)
        alert_sms.sms_sent = djangotime.now() - djangotime.timedelta(days=20)
        alert_sms.save()

        # refresh automated tasks to get new alert templates
        task_template_email = AutomatedTask.objects.get(pk=task_template_email.pk)  # type: ignore
        task_template_dashboard_text = AutomatedTask.objects.get(pk=task_template_dashboard_text.pk)  # type: ignore
        task_template_blank = AutomatedTask.objects.get(pk=task_template_blank.pk)  # type: ignore

        Alert.handle_alert_failure(task_template_email)  # type: ignore
        Alert.handle_alert_failure(task_template_dashboard_text)  # type: ignore

        outage_email.assert_called_with(pk=alert_email.pk, alert_interval=1)
        outage_sms.assert_called_with(pk=alert_sms.pk, alert_interval=1)
        outage_email.reset_mock()
        outage_sms.reset_mock()

        # test resolving alerts
        Alert.handle_alert_resolve(task_agent)  # type: ignore

        self.assertTrue(Alert.objects.get(assigned_task=task_agent).resolved)
        self.assertTrue(Alert.objects.get(assigned_task=task_agent).resolved_on)

        resolved_sms.assert_not_called()
        resolved_email.assert_not_called()

        # test resolved notifications
        alert_template_email.task_email_on_resolved = True  # type: ignore
        alert_template_email.save()  # type: ignore

        alert_template_dashboard_text.task_text_on_resolved = True  # type: ignore
        alert_template_dashboard_text.save()  # type: ignore

        # refresh automated tasks to get new alert templates
        task_template_email = AutomatedTask.objects.get(pk=task_template_email.pk)  # type: ignore
        task_template_dashboard_text = AutomatedTask.objects.get(pk=task_template_dashboard_text.pk)  # type: ignore
        task_template_blank = AutomatedTask.objects.get(pk=task_template_blank.pk)  # type: ignore

        Alert.handle_alert_resolve(task_template_email)  # type: ignore

        resolved_email.assert_called_with(pk=alert_email.pk)
        resolved_sms.assert_not_called()
        resolved_email.reset_mock()

        Alert.handle_alert_resolve(task_template_dashboard_text)  # type: ignore

        resolved_sms.assert_called_with(pk=alert_sms.pk)
        resolved_email.assert_not_called()

        # call the email and sms tasks synchronously
        handle_resolved_task_sms_alert(pk=alert_sms.pk)
        handle_resolved_task_email_alert(pk=alert_email.pk)

        send_email.assert_called()
        send_sms.assert_called()

    @patch("core.models.TwClient")
    @patch("smtplib.SMTP")
    def test_override_core_settings(self, smtp, sms):
        from core.models import CoreSettings

        # setup data
        alert_template = baker.make(
            "alerts.AlertTemplate",
            email_recipients=["example@example.com"],
            text_recipients=["+12321233212"],
            email_from="from@email.com",
        )

        core = CoreSettings.objects.first()
        core.smtp_host = "test.test.com"
        core.smtp_port = 587
        core.smtp_recipients = ["recipient@test.com"]
        core.twilio_account_sid = "test"
        core.twilio_auth_token = "1234123412341234"
        core.sms_alert_recipients = ["+1234567890"]

        # test sending email with alert template settings
        core.send_mail("Test", "Test", alert_template=alert_template)

        core.send_sms("Test", alert_template=alert_template)

    @patch("agents.models.Agent.nats_cmd")
    @patch("agents.tasks.agent_outage_sms_task.delay")
    @patch("agents.tasks.agent_outage_email_task.delay")
    @patch("agents.tasks.agent_recovery_email_task.delay")
    @patch("agents.tasks.agent_recovery_sms_task.delay")
    def test_alert_actions(
        self, recovery_sms, recovery_email, outage_email, outage_sms, nats_cmd
    ):

        from agents.tasks import agent_outages_task

        # Setup cmd mock
        success = {
            "retcode": 0,
            "stdout": "success!",
            "stderr": "",
            "execution_time": 5.0000,
        }

        nats_cmd.side_effect = ["pong", success]

        # setup data
        agent = baker.make_recipe(
            "agents.overdue_agent", version=settings.LATEST_AGENT_VER
        )
        failure_action = baker.make_recipe("scripts.script")
        resolved_action = baker.make_recipe("scripts.script")
        alert_template = baker.make(
            "alerts.AlertTemplate",
            is_active=True,
            agent_always_alert=True,
            action=failure_action,
            action_timeout=30,
            resolved_action=resolved_action,
            resolved_action_timeout=35,
            resolved_action_args=["nice_arg"],
        )
        agent.client.alert_template = alert_template
        agent.client.save()

        agent.set_alert_template()

        agent_outages_task()

        # this is what data should be
        data = {
            "func": "runscriptfull",
            "timeout": 30,
            "script_args": [],
            "payload": {"code": failure_action.code, "shell": failure_action.shell},
        }

        nats_cmd.assert_called_with(data, timeout=30, wait=True)

        nats_cmd.reset_mock()

        # Setup cmd mock
        success = {
            "retcode": 0,
            "stdout": "success!",
            "stderr": "",
            "execution_time": 5.0000,
        }

        nats_cmd.side_effect = ["pong", success]

        # make sure script run results were stored
        alert = Alert.objects.get(agent=agent)
        self.assertEqual(alert.action_retcode, 0)
        self.assertEqual(alert.action_execution_time, "5.0000")
        self.assertEqual(alert.action_stdout, "success!")
        self.assertEqual(alert.action_stderr, "")

        # resolve alert and test
        agent.last_seen = djangotime.now()
        agent.save()

        url = "/api/v3/checkin/"

        data = {
            "agent_id": agent.agent_id,
            "version": settings.LATEST_AGENT_VER,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        # this is what data should be
        data = {
            "func": "runscriptfull",
            "timeout": 35,
            "script_args": ["nice_arg"],
            "payload": {"code": resolved_action.code, "shell": resolved_action.shell},
        }

        nats_cmd.assert_called_with(data, timeout=35, wait=True)

        # make sure script run results were stored
        alert = Alert.objects.get(agent=agent)
        self.assertEqual(alert.resolved_action_retcode, 0)
        self.assertEqual(alert.resolved_action_execution_time, "5.0000")
        self.assertEqual(alert.resolved_action_stdout, "success!")
        self.assertEqual(alert.resolved_action_stderr, "")

    def test_parse_script_args(self):
        alert = baker.make("alerts.Alert")

        args = ["-Parameter", "-Another {{alert.id}}"]

        # test default value
        self.assertEqual(
            ["-Parameter", f"-Another '{alert.id}'"],  # type: ignore
            alert.parse_script_args(args=args),  # type: ignore
        )
