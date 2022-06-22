from django.db import migrations

from tacticalrmm.constants import GoArch


def change_arch(apps, schema_editor):
    Deployment = apps.get_model("clients", "Deployment")
    for d in Deployment.objects.all():
        if d.arch == "64":
            d.arch = GoArch.AMD64
        else:
            d.arch = GoArch.i386

        d.save(update_fields=["arch"])


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0021_remove_client_agent_count_remove_site_agent_count"),
    ]

    operations = [
        migrations.RunPython(change_arch),
    ]
