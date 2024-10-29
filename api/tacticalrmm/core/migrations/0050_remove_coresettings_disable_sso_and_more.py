# Generated by Django 4.2.14 on 2024-10-15 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_coresettings_disable_sso'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coresettings',
            name='disable_sso',
        ),
        migrations.AddField(
            model_name='coresettings',
            name='sso_enabled',
            field=models.BooleanField(default=False),
        ),
    ]