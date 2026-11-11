from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0044_copy_mesh_permission_to_file_browser"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="language",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Auto"),
                    ("en-US", "English"),
                    ("pt-BR", "Português (Brasil)"),
                ],
                default="",
                max_length=10,
            ),
        ),
    ]
