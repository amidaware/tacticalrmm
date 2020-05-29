from django.db import models

SCRIPT_SHELLS = [
    ("powershell", "Powershell"),
    ("cmd", "Batch (CMD)"),
    ("python", "Python"),
]


class Script(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    filename = models.CharField(max_length=255)
    shell = models.CharField(
        max_length=100, choices=SCRIPT_SHELLS, default="powershell"
    )

    @property
    def filepath(self):
        return f"salt://scripts//userdefined//{self.filename}"

    @property
    def file(self):
        return f"/srv/salt/scripts/userdefined/{self.filename}"

    @staticmethod
    def validate_filename(filename):
        if (
            not filename.endswith(".py")
            and not filename.endswith(".ps1")
            and not filename.endswith(".bat")
        ):
            return False

        return True

    def __str__(self):
        return self.filename
