from drf_spectacular.extensions import OpenApiAuthenticationExtension


# custom api key auth for swagger-ui
class APIAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "tacticalrmm.auth.APIAuthentication"  # full import path OR class ref
    name = "API Key Auth"  # name used in the schem

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-KEY",
        }
