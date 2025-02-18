import autotasks.models
import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("autotasks", "0040_alter_taskresult_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="automatedtask",
            name="task_supported_platforms",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("windows", "Windows"),
                        ("linux", "Linux"),
                        ("darwin", "macOS"),
                    ],
                    max_length=30,
                ),
                default=autotasks.models.default_task_supported_platforms,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="taskresult",
            name="locked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskresult",
            name="run_status",
            field=models.CharField(
                blank=True,
                choices=[("running", "Running"), ("completed", "Completed")],
                max_length=30,
                null=True,
            ),
        ),
    ]
