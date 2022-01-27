from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
import requests
import json
from ..models import Integration

class GetHardware(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "hardware?limit=500&offset=0&order=desc&status=" + request.query_params["status"],
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)


    def post(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "requestable": False,
            "asset_tag": request.data["asset_tag"],
            "status_id": request.data["status_id"],
            "model_id": request.data["model_id"],
            "name": request.data["name"],
            "serial": request.data["serial"],
            "rtd_location_id": request.data["rtd_location_id"],
            "company_id": request.data["company_id"],
            "manufacturer_id": request.data["manufacturer_id"],
            "supplier_id": request.data["supplier_id"],
            "purchase_cost": request.data["purchase_cost"],
            "purchase_date": request.data["purchase_date"],
            "warranty_months": request.data["warranty_months"],
            "order_number": request.data["order_number"]
        }
        
        result = requests.post(
            integration.base_url + "hardware",
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetAsset(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, asset_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "hardware/" + asset_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def put(self, request, asset_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "requestable": False,
            "asset_tag": request.data["asset_tag"],
            "status_id": request.data["status_id"],
            "model_id": request.data["model_id"],
            "name": request.data["name"],
            "serial": request.data["serial"],
            "rtd_location_id": request.data["rtd_location_id"],
            "company_id": request.data["company_id"],
            "manufacturer_id": request.data["manufacturer_id"],
            "supplier_id": request.data["supplier_id"],
            "purchase_cost": request.data["purchase_cost"],
            "purchase_date": request.data["purchase_date"],
            "warranty_months": request.data["warranty_months"],
            "order_number": request.data["order_number"]
        }

        result = requests.put(
            integration.base_url + "hardware/" + asset_id,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def delete(self, request, asset_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.delete(
            integration.base_url + "hardware/" + asset_id,

            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetAssetByTag(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, asset_tag, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "hardware/bytag/" + asset_tag,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetAssetCheckout(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, asset_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "id": asset_id,
            "checkout_to_type": request.data["checkout_to_type"],
            "checkout_at": request.data["checkout_at"],
            "expected_checkin": request.data["expected_checkin"],
            "note": request.data["note"]
        }

        if request.data['assigned_user']:
            payload['assigned_user'] = request.data["assigned_user"]
        elif request.data['assigned_location']:
            payload['assigned_location'] = request.data["assigned_location"]
        else:
            payload['assigned_asset'] = request.data["assigned_asset"]

        result = requests.post(
            integration.base_url + "hardware/" + asset_id + "/checkout",
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)


class GetAssetCheckin(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, asset_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "id": asset_id,
            "location_id": request.data["location_id"],
            "note": request.data["note"]
        }

        result = requests.post(
            integration.base_url + "hardware/" + asset_id + "/checkin",
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetCompanies(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "companies/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetCompany(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, company_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "companies/" + company_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def patch(self, request, company_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "name": request.data["name"]
        }

        result = requests.patch(
            integration.base_url + "companies/" + company_id,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)


    def delete(self, request, company_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.delete(
            integration.base_url + "companies/" + company_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetStatusLabels(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "statuslabels/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetCategories(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "categories/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetModels(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "models/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def post(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "name": request.data["model_name"],
            "model_number": request.data["model_number"],
            "category_id": request.data["category_id"],
            "manufacturer_id": request.data["manufacturer_id"]
        }

        result = requests.post(
            integration.base_url + "models",
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetModel(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, model_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "models/" + model_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def put(self, request, model_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "name": request.data["name"],
            "model_number": request.data["model_number"],
            "category_id": request.data["category_id"],
            "manufacturer_id": request.data["manufacturer_id"]
        }

        result = requests.put(
            integration.base_url + "models/" + model_id,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def delete(self, request, model_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.delete(
            integration.base_url + "models/" + model_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetManufacturers(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "manufacturers/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetSuppliers(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "suppliers/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetMaintenances(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "maintenances/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def post(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "title": request.data["title"],
            "asset_maintenance_type": request.data["asset_maintenance_type"],
            "asset_id": request.data["asset_id"],
            "supplier_id": request.data["supplier_id"],
            "start_date": request.data["start_date"],
            "completion_date": request.data["completion_date"],
            "cost": request.data["cost"],
            "notes": request.data["notes"]
        }

        result = requests.post(
            integration.base_url + "maintenances",
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)


class GetMaintenance(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, maintenance_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "maintenances/" + maintenance_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def patch(self, request, maintenance_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "title": request.data["title"],
            "asset_maintenance_type": request.data["asset_maintenance_type"],
            "asset_id": request.data["asset_id"],
            "supplier_id": request.data["supplier_id"],
            "start_date": request.data["start_date"],
            "completion_date": request.data["completion_date"],
            "cost": request.data["cost"],
            "notes": request.data["notes"]
        }

        result = requests.patch(
            integration.base_url + "maintenances/" + maintenance_id,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def delete(self, request, maintenance_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.delete(
            integration.base_url + "maintenances/" + maintenance_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetLocations(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "locations/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetLocation(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, location_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "locations/" + location_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def patch(self, request, location_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "name": request.data["name"]
        }

        result = requests.patch(
            integration.base_url + "locations/" + location_id,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def delete(self, request, location_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.delete(
            integration.base_url + "locations/" + location_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetUsers(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "users/",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

class GetUser(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.get(
            integration.base_url + "users/" + user_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def patch(self, request, user_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        payload = {
            "first_name": request.data["first_name"],
            "last_name": request.data["last_name"],
            "jobtitle": request.data["jobtitle"],
            "department": request.data["department"]
            }

        result = requests.patch(
            integration.base_url + "users/" + user_id,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)

    def delete(self, request, user_id, format=None):
        integration = Integration.objects.get(name="Snipe-IT")

        result = requests.delete(
            integration.base_url + "users/" + user_id,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)