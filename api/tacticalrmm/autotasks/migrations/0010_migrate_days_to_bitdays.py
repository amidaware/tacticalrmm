from django.db import migrations

from tacticalrmm.utils import get_bit_days

DAYS_OF_WEEK = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def migrate_days(apps, schema_editor):
    AutomatedTask = apps.get_model("autotasks", "AutomatedTask")
    for task in AutomatedTask.objects.exclude(run_time_days__isnull=True).exclude(
        run_time_days=[]
    ):
        run_days = [DAYS_OF_WEEK.get(day) for day in task.run_time_days]
        task.run_time_bit_weekdays = get_bit_days(run_days)
        task.save(update_fields=["run_time_bit_weekdays"])


class Migration(migrations.Migration):

    dependencies = [
        ("autotasks", "0009_automatedtask_run_time_bit_weekdays"),
    ]

    operations = [
        migrations.RunPython(migrate_days),
    ]
