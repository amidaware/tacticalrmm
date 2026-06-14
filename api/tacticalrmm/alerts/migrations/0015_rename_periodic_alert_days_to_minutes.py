from django.db import migrations, models


def convert_days_to_minutes(apps, schema_editor):
    AlertTemplate = apps.get_model("alerts", "AlertTemplate")
    for obj in AlertTemplate.objects.all():
        if obj.agent_periodic_alert_days:
            obj.agent_periodic_alert_days = obj.agent_periodic_alert_days * 1440
        if obj.check_periodic_alert_days:
            obj.check_periodic_alert_days = obj.check_periodic_alert_days * 1440
        if obj.task_periodic_alert_days:
            obj.task_periodic_alert_days = obj.task_periodic_alert_days * 1440
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0014_alerttemplate_action_rest_alerttemplate_action_type_and_more"),
    ]

    operations = [
        migrations.RunPython(
            convert_days_to_minutes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RenameField(
            model_name="alerttemplate",
            old_name="agent_periodic_alert_days",
            new_name="agent_periodic_alert_minutes",
        ),
        migrations.RenameField(
            model_name="alerttemplate",
            old_name="check_periodic_alert_days",
            new_name="check_periodic_alert_minutes",
        ),
        migrations.RenameField(
            model_name="alerttemplate",
            old_name="task_periodic_alert_days",
            new_name="task_periodic_alert_minutes",
        ),
    ]
