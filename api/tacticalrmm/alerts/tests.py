from datetime import datetime, timedelta
from unittest.mock import patch
from django.utils import timezone as djangotime
from model_bakery import baker, seq
from django.conf import settings

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
        self.assertEquals(resp.data["alerts"], AlertSerializer(alerts, many=True).data)
        self.assertEquals(resp.data["alerts_count"], 10)

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
            self.assertEqual(len(resp.data), req["count"])

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
        url = f"/alerts/alerts/{alert.pk}/"

        resp = self.client.get(url, format="json")
        serializer = AlertSerializer(alert)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_update_alert(self):
        # returns 404 for invalid alert pk
        resp = self.client.put("/alerts/alerts/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        alert = baker.make("alerts.Alert", resolved=False, snoozed=False)

        url = f"/alerts/alerts/{alert.pk}/"

        # test resolving alert
        data = {
            "id": alert.pk,
            "type": "resolve",
        }
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Alert.objects.get(pk=alert.pk).resolved)
        self.assertTrue(Alert.objects.get(pk=alert.pk).resolved_on)

        # test snoozing alert
        data = {"id": alert.pk, "type": "snooze", "snooze_days": "30"}
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Alert.objects.get(pk=alert.pk).snoozed)
        self.assertTrue(Alert.objects.get(pk=alert.pk).snooze_until)

        # test snoozing alert without snooze_days
        data = {"id": alert.pk, "type": "snooze"}
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        # test unsnoozing alert
        data = {"id": alert.pk, "type": "unsnooze"}
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Alert.objects.get(pk=alert.pk).snoozed)
        self.assertFalse(Alert.objects.get(pk=alert.pk).snooze_until)

        # test invalid type
        data = {"id": alert.pk, "type": "invalid"}
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("put", url)

    def test_delete_alert(self):
        # returns 404 for invalid alert pk
        resp = self.client.put("/alerts/alerts/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        alert = baker.make("alerts.Alert")

        # test delete alert
        url = f"/alerts/alerts/{alert.pk}/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        self.assertFalse(Alert.objects.filter(pk=alert.pk).exists())
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
            "alerts": [alert.pk for alert in alerts],
            "snooze_days": "30",
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Alert.objects.filter(snoozed=False).exists())

        # test bulk resolving alerts
        data = {"bulk_action": "resolve", "alerts": [alert.pk for alert in alerts]}

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
        self.assertEqual(resp.data, serializer.data)

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
        url = f"/alerts/alerttemplates/{alert_template.pk}/"

        resp = self.client.get(url, format="json")
        serializer = AlertTemplateSerializer(alert_template)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        self.check_not_authenticated("get", url)

    def test_update_alert_template(self):
        # returns 404 for invalid alert pk
        resp = self.client.put("/alerts/alerttemplates/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        alert_template = baker.make("alerts.AlertTemplate")

        url = f"/alerts/alerttemplates/{alert_template.pk}/"

        # test data
        data = {
            "id": alert_template.pk,
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
        url = f"/alerts/alerttemplates/{alert_template.pk}/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)

        self.assertFalse(AlertTemplate.objects.filter(pk=alert_template.pk).exists())

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

        url = f"/alerts/alerttemplates/{alert_template.pk}/related/"

        resp = self.client.get(url, format="json")
        serializer = AlertTemplateRelationSerializer(alert_template)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.assertEqual(len(resp.data["policies"]), 1)
        self.assertEqual(len(resp.data["clients"]), 2)
        self.assertEqual(len(resp.data["sites"]), 3)
        self.assertTrue(
            AlertTemplate.objects.get(pk=alert_template.pk).is_default_template
        )


class TestAlertTasks(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()
        core = CoreSettings.objects.first()
        core.twilio_account_sid = "test"
        core.twilio_auth_token = "test"
        core.text_recipients = ["+12314567890"]
        core.email_recipients = ["test@example.com"]
        core.twilio_number = "+12314567890"
        core.save()

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
                pk__in=[alert.pk for alert in not_snoozed], snoozed=False
            ).exists()
        )
        self.assertTrue(
            Alert.objects.filter(
                pk__in=[alert.pk for alert in snoozed], snoozed=False
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
        self.assertFalse(workstation.get_alert_template())
        self.assertFalse(server.get_alert_template())

        # assign first Alert Template as to a policy and apply it as default
        policy.alert_template = alert_templates[0]
        policy.save()
        core.workstation_policy = policy
        core.server_policy = policy
        core.save()

        self.assertEquals(server.get_alert_template().pk, alert_templates[0].pk)
        self.assertEquals(workstation.get_alert_template().pk, alert_templates[0].pk)

        # assign second Alert Template to as default alert template
        core.alert_template = alert_templates[1]
        core.save()

        self.assertEquals(workstation.get_alert_template().pk, alert_templates[1].pk)
        self.assertEquals(server.get_alert_template().pk, alert_templates[1].pk)

        # assign third Alert Template to client
        workstation.client.alert_template = alert_templates[2]
        server.client.alert_template = alert_templates[2]
        workstation.client.save()
        server.client.save()

        self.assertEquals(workstation.get_alert_template().pk, alert_templates[2].pk)
        self.assertEquals(server.get_alert_template().pk, alert_templates[2].pk)

        # apply policy to client and should override
        workstation.client.workstation_policy = policy
        server.client.server_policy = policy
        workstation.client.save()
        server.client.save()

        self.assertEquals(workstation.get_alert_template().pk, alert_templates[0].pk)
        self.assertEquals(server.get_alert_template().pk, alert_templates[0].pk)

        # assign fouth Alert Template to site
        workstation.site.alert_template = alert_templates[3]
        server.site.alert_template = alert_templates[3]
        workstation.site.save()
        server.site.save()

        self.assertEquals(workstation.get_alert_template().pk, alert_templates[3].pk)
        self.assertEquals(server.get_alert_template().pk, alert_templates[3].pk)

        # apply policy to site
        workstation.site.workstation_policy = policy
        server.site.server_policy = policy
        workstation.site.save()
        server.site.save()

        self.assertEquals(workstation.get_alert_template().pk, alert_templates[0].pk)
        self.assertEquals(server.get_alert_template().pk, alert_templates[0].pk)

        # apply policy to agents
        workstation.policy = policy
        server.policy = policy
        workstation.save()
        server.save()

        self.assertEquals(workstation.get_alert_template().pk, alert_templates[0].pk)
        self.assertEquals(server.get_alert_template().pk, alert_templates[0].pk)

        # test disabling alert template
        alert_templates[0].is_active = False
        alert_templates[0].save()

        self.assertEquals(workstation.get_alert_template().pk, alert_templates[3].pk)
        self.assertEquals(server.get_alert_template().pk, alert_templates[3].pk)

        # test policy exclusions
        alert_templates[3].excluded_agents.set([workstation.pk])

        self.assertEquals(workstation.get_alert_template().pk, alert_templates[2].pk)
        self.assertEquals(server.get_alert_template().pk, alert_templates[3].pk)

        # test workstation exclusions
        alert_templates[2].exclude_workstations = True
        alert_templates[2].save()

        self.assertEquals(workstation.get_alert_template().pk, alert_templates[1].pk)
        self.assertEquals(server.get_alert_template().pk, alert_templates[3].pk)

        # test server exclusions
        alert_templates[3].exclude_servers = True
        alert_templates[3].save()

        self.assertEquals(workstation.get_alert_template().pk, alert_templates[1].pk)
        self.assertEquals(server.get_alert_template().pk, alert_templates[2].pk)

    @patch("agents.tasks.sleep")
    @patch("smtplib.SMTP")
    @patch("core.models.TwClient")
    @patch("agents.tasks.agent_outage_sms_task.delay")
    @patch("agents.tasks.agent_outage_email_task.delay")
    @patch("agents.tasks.agent_recovery_email_task.delay")
    @patch("agents.tasks.agent_recovery_sms_task.delay")
    def test_handle_agent_offline_alerts(
        self, recovery_sms, recovery_email, outage_email, outage_sms, TwClient, SMTP, sleep
    ):
        from agents.tasks import (
            agent_outages_task,
            agent_outage_sms_task,
            agent_outage_email_task,
            agent_recovery_sms_task,
            agent_recovery_email_task,
        )
        from alerts.models import Alert

        # setup sms and email mock objects
        TwClient.messages.create.return_value.sid = "SomeRandomText"
        SMTP.return_value = True

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
            "alerts.AlertTemplate", is_active=True, agent_always_text=True, agent_periodic_alert_days=5
        )
        alert_template_always_email = baker.make(
            "alerts.AlertTemplate", is_active=True, agent_always_email=True, agent_periodic_alert_days=5
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

        SMTP.reset_mock()
        TwClient.reset_mock()

        # calling agent outage task again shouldn't create duplicate alerts and won't send alerts
        agent_outages_task()
        self.assertEquals(Alert.objects.count(), 6)

        SMTP.assert_not_called()
        TwClient.assert_not_called()

        # test periodic notification

        # change email/text sent to sometime in the past
        alert_text = Alert.objects.get(agent=agent_template_text)
        alert_text.sms_sent = djangotime.now() - djangotime.timedelta(days=20)
        alert_text.save()
        alert_email = Alert.objects.get(agent=agent_template_email)
        alert_email.email_sent = djangotime.now() - djangotime.timedelta(days=20)
        alert_email.save()

        agent_outages_task()

        print(outage_sms.call_count)
        print(outage_email.call_count)

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

        self.assertEquals(SMTP.call_count, 1)
        self.assertEquals(TwClient.call_count, 1)

        # test resolved alerts
        # alter the alert template to email and test on resolved
        alert_template_always_email.agent_email_on_resolved = True
        alert_template_always_email.save()
        alert_template_always_text.agent_text_on_resolved = True
        alert_template_always_text.save()

        # have the two agents checkin
        url = "/api/v3/checkin/"

        agent_template_text.version = settings.LATEST_AGENT_VER
        agent_template_text.save()
        agent_template_email.version = settings.LATEST_AGENT_VER
        agent_template_email.save()

        data = {
            "agent_id": agent_template_text.agent_id,
            "version": settings.LATEST_AGENT_VER
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        data = {
            "agent_id": agent_template_email.agent_id,
            "version": settings.LATEST_AGENT_VER
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
        self.assertTrue(Alert.objects.get(agent=agent_template_email).resolved_email_sent)

    def test_handle_check_alerts(self):
        pass

    def test_handle_task_alerts(self):
        pass

    def test_override_email_settings(self):
        pass
