from django.db import models

class Client(models.Model):
    client = models.CharField(max_length=255)
    checks_failing = models.BooleanField(default=False)

    def __str__(self):
        return self.client

class Site(models.Model):
    client = models.ForeignKey(Client, related_name="sites", on_delete=models.CASCADE)
    site = models.CharField(max_length=255)
    checks_failing = models.BooleanField(default=False)

    def __str__(self):
        return self.site