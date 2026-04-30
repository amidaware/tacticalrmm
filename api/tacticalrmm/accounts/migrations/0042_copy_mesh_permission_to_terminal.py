from django.db import migrations


def copy_can_use_mesh_to_terminal(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(can_use_mesh=True).update(can_use_terminal=True)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0041_role_can_use_terminal"),
    ]

    operations = [
        migrations.RunPython(
            copy_can_use_mesh_to_terminal,
            reverse_code=migrations.RunPython.noop,
        ),
    ]