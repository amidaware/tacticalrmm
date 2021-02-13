from datetime import datetime, timedelta
from core.models import CoreSettings

from django.utils import timezone as djangotime
from tacticalrmm.test import TacticalTestCase
from model_bakery import baker, seq

from .models import Alert, AlertTemplate
from .serializers import (
    AlertSerializer,
    AlertTemplateSerializer,
    AlertTemplateRelationSerializer,
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
