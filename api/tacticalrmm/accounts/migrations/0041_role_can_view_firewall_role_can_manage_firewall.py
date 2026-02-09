from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0040_role_can_use_registry"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="can_view_firewall",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="role",
            name="can_manage_firewall",
            field=models.BooleanField(default=False),
        ),
    ]
