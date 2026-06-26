from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0053_coresettings_terminal_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="coresettings",
            name="email_body_template",
            field=models.CharField(max_length=2048, blank=True, default="{body}"),
        ),
        migrations.AddField(
            model_name="coresettings",
            name="email_subject_template",
            field=models.CharField(max_length=255, blank=True, default="{subject}"),
        ),
        migrations.AddField(
            model_name="coresettings",
            name="check_email_subject_template",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="coresettings",
            name="check_email_body_template",
            field=models.CharField(max_length=2048, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="coresettings",
            name="task_email_subject_template",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="coresettings",
            name="task_email_body_template",
            field=models.CharField(max_length=2048, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="coresettings",
            name="agent_outage_email_subject_template",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="coresettings",
            name="agent_outage_email_body_template",
            field=models.CharField(max_length=2048, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="coresettings",
            name="agent_recovery_email_subject_template",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="coresettings",
            name="agent_recovery_email_body_template",
            field=models.CharField(max_length=2048, blank=True, default=""),
        ),
    ]