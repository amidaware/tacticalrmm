# Generated by Django 4.2.11 on 2024-04-05 05:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0024_alter_deployment_goarch'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='trayicon',
            field=models.JSONField(default=list),
        ),
    ]