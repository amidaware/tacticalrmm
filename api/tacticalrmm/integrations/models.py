from django.db import models
import base64

class Integration(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField(max_length=255)
    configuration = models.JSONField(null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name
        
    @property
    def api_key(self):
        return self.configuration["api_key"]

    @property
    def auth(self):
        return base64.b64encode((self.api_key + ":").encode("UTF-8")).decode("UTF-8")

    @property
    def base_url(self):
        return self.configuration["api_url"]

    @property
    def company_id(self):
        return self.configuration["company_id"]

    @property
    def auth_header(self):
        return "Basic " + self.auth