from django.db import migrations


def migrate_env_vars(apps, schema_editor):
    AutomatedTask = apps.get_model("autotasks", "AutomatedTask")
    for task in AutomatedTask.objects.iterator(chunk_size=30):
        try:
            tmp = []
            if isinstance(task.actions, list) and task.actions:
                for t in task.actions:
                    if isinstance(t, dict):
                        if t["type"] == "script":
                            try:
                                t["env_vars"]
                            except KeyError:
                                t["env_vars"] = []
                        tmp.append(t)
            if tmp:
                task.actions = tmp
                task.save(update_fields=["actions"])
        except Exception as e:
            print(f"ERROR: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ("autotasks", "0037_alter_taskresult_retcode"),
    ]

    operations = [
        migrations.RunPython(migrate_env_vars),
    ]
