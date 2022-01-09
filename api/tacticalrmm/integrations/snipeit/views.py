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
            integration.base_url + "hardware?limit=500&offset=0&order=desc&status=" + request.query_params['status'],
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {integration.api_key.strip()}"
            },
        ).json()

        return Response(result)


    def post(self, request, format=None):
        integration = Integration.objects.get(name="Snipe-IT")
        print(request.data)
        payload = {
            "requestable": False,
            "asset_tag": request.data['asset_tag'],
            "status_id": request.data['status_id'],
            "model_id": request.data['model_id'],
            "name": request.data['name'],
            "serial": request.data['serial'],
            "location_id": request.data['location_id'],
            "company_id": request.data['company_id']
        }
        print(request.data)
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
            "name": request.data['name'],
            "assetTag": request.data['assetTag'],
            "serial": request.data['serial'],
            "purchaseCost": request.data['purchaseCost'],
            "warranty": request.data['warranty']
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
<<<<<<< HEAD
<<<<<<< HEAD
            json=payload,
=======
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
>>>>>>> checkin/checkout and delete asset
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
        print(request.data)
        payload = {
            "id": asset_id,
            "checkout_to_type": request.data['checkout_to_type'],
<<<<<<< HEAD
<<<<<<< HEAD
            "assigned_user": 3,
=======
            "assigned_user": request.data['assigned_user'],
>>>>>>> 5a541b0209a0de11b20c5d153af1efa9333fd4ab
=======
            "assigned_user": request.data['assigned_user'],
>>>>>>> allow Meraki integration dashboard at client level as well as agent
            "checkout_at": request.data['checkout_at'],
            "expected_checkin": request.data['expected_checkin'],
            "note": request.data['note']
        }

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
        print(request.data)
        payload = {
            "id": asset_id,
            "location_id": request.data['location_id'],
            "note": request.data['note']
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
            "name": request.data['name']
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
        print(request.data['model_name'])
        payload = {
            "name": request.data['model_name'],
            "model_number": request.data['model_number'],
            "category_id": request.data['category_id'],
            "manufacturer_id": request.data['manufacturer_id']
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
            "name": request.data['name']
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
            "first_name": request.data['first_name'],
            "last_name": request.data['last_name'],
            "jobtitle": request.data['jobtitle'],
            "department": request.data['department']
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