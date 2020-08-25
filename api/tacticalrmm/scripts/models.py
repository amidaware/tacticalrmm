from django.db import models

SCRIPT_SHELLS = [
    ("powershell", "Powershell"),
    ("cmd", "Batch (CMD)"),
    ("python", "Python"),
]

SCRIPT_TYPES = [
    ("userdefined", "User Defined"),
    ("builtin", "Built In"),
]


class Script(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    filename = models.CharField(max_length=255)
    shell = models.CharField(
        max_length=100, choices=SCRIPT_SHELLS, default="powershell"
    )
    script_type = models.CharField(
        max_length=100, choices=SCRIPT_TYPES, default="userdefined"
    )

    def __str__(self):
        return self.filename

    @property
    def filepath(self):
        # for the windows agent when using 'salt-call'
        if self.script_type == "userdefined":
            return f"salt://scripts//userdefined//{self.filename}"
        else:
            return f"salt://scripts//{self.filename}"

    @property
    def file(self):
        if self.script_type == "userdefined":
            return f"/srv/salt/scripts/userdefined/{self.filename}"
        else:
            return f"/srv/salt/scripts/{self.filename}"

    @property
    def code(self):
        try:
            with open(self.file, "r") as f:
                text = f.read()
        except:
            text = "n/a"

        return text
