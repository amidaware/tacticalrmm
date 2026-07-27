from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agents", "0062_agent_default_shell_agent_default_shell_custom"),
    ]

    operations = [
        migrations.AddField(
            model_name="agent",
            name="ai_notes",
            field=models.TextField(blank=True, default=""),
        ),
    ]
