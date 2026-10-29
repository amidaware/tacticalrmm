# Generated manually for report schedule send conditions

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0004_reportdataquery_created_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="reportschedule",
            name="conditions",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(),
                blank=True,
                default=list,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="reportschedule",
            name="last_run_message",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="reportschedule",
            name="last_run_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("success", "Success"),
                    ("skipped", "Skipped"),
                    ("error", "Error"),
                ],
                default="",
                max_length=20,
            ),
        ),
    ]
