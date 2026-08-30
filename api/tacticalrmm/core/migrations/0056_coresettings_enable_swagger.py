from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0055_coresettings_ssh_gateway_enable_exec_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="coresettings",
            name="enable_swagger",
            field=models.BooleanField(default=False),
        ),
    ]