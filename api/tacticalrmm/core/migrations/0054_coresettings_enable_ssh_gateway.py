# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0053_coresettings_terminal_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="coresettings",
            name="enable_ssh_gateway",
            field=models.BooleanField(default=False),
        ),
    ]
