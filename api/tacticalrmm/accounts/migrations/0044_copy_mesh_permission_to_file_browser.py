from django.db import migrations


def copy_can_use_mesh_to_file_browser(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(can_use_mesh=True).update(can_use_file_browser=True)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0043_role_can_use_file_browser"),
    ]

    operations = [
        migrations.RunPython(
            copy_can_use_mesh_to_file_browser,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
