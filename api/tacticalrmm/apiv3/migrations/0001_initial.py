# Generated by Django 4.2.11 on 2024-04-05 05:18

import apiv3.support.models
import apiv3.support.utils
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SysTray',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=200, null=True)),
                ('icon', models.FileField(blank=True, null=True, storage=apiv3.support.utils.get_systray_assets_fs, unique=True, upload_to='', validators=[apiv3.support.models.validate_ico_file])),
            ],
        ),
    ]