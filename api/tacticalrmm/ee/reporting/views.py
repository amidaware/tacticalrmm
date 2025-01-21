"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import json
import os
import shutil
import uuid
from typing import Any, Dict, List, Literal, Optional, Union

import requests
from django.conf import settings as djangosettings
from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
    SuspiciousFileOperation,
)
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from jinja2.exceptions import TemplateError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import (
    BooleanField,
    CharField,
    ChoiceField,
    IntegerField,
    JSONField,
    ListField,
    ModelSerializer,
    Serializer,
    ValidationError,
)
from rest_framework.views import APIView
from tacticalrmm.utils import notify_error

from .models import ReportAsset, ReportDataQuery, ReportHTMLTemplate, ReportTemplate
from .permissions import GenerateReportPerms, ReportingPerms
from .storage import report_assets_fs
from .utils import (
    _import_assets,
    _import_base_template,
    _import_report_template,
    base64_encode_assets,
    generate_html,
    generate_pdf,
    normalize_asset_url,
    prep_variables_for_template,
)


def path_exists(value: str) -> None:
    if not report_assets_fs.exists(value):
        raise ValidationError("Path does not exist on the file system")


class ReportTemplateSerializer(ModelSerializer[ReportTemplate]):
    class Meta:
        model = ReportTemplate
        fields = "__all__"


class GetAddReportTemplate(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer

    def get(self, request: Request) -> Response:
        depends_on: List[str] = request.query_params.getlist("dependsOn[]", [])

        if depends_on:
            templates = ReportTemplate.objects.filter(depends_on__overlap=depends_on)
        else:
            templates = ReportTemplate.objects.all()
        return Response(ReportTemplateSerializer(templates, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = ReportTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save()

        return Response(ReportTemplateSerializer(response).data)


class GetEditDeleteReportTemplate(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer

    def get(self, request: Request, pk: int) -> Response:
        template = get_object_or_404(ReportTemplate, pk=pk)

        return Response(ReportTemplateSerializer(template).data)

    def put(self, request: Request, pk: int) -> Response:
        template = get_object_or_404(ReportTemplate, pk=pk)

        serializer = ReportTemplateSerializer(
            instance=template, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        response = serializer.save()

        return Response(ReportTemplateSerializer(response).data)

    def delete(self, request: Request, pk: int) -> Response:
        get_object_or_404(ReportTemplate, pk=pk).delete()

        return Response()


class GenerateReport(APIView):
    permission_classes = [IsAuthenticated, GenerateReportPerms]

    def post(self, request: Request, pk: int) -> Union[FileResponse, Response]:
        template = get_object_or_404(ReportTemplate, pk=pk)

        format = request.data["format"]

        if format not in ("pdf", "html", "plaintext"):
            return notify_error("Report format is incorrect.")

        try:
            html_report, _ = generate_html(
                template=template.template_md,
                template_type=template.type,
                css=template.template_css or "",
                html_template=(
                    template.template_html.id if template.template_html else None
                ),
                variables=template.template_variables,
                dependencies=request.data["dependencies"],
            )

            html_report = normalize_asset_url(html_report, format)

            if format != "pdf":
                return Response(html_report)
            else:
                pdf_bytes = generate_pdf(html=html_report)

                return FileResponse(
                    ContentFile(pdf_bytes),
                    content_type="application/pdf",
                    filename=f"{template.name}.pdf",
                )

        except TemplateError as error:
            if hasattr(error, "lineno"):
                return notify_error(f"Line {error.lineno}: {error.message}")
            else:
                return notify_error(str(error))
        except Exception as error:
            return notify_error(str(error))


class GenerateReportPreview(APIView):
    permission_classes = [IsAuthenticated, GenerateReportPerms]

    class InputRequest:
        template_md: str
        type: Literal["markdown", "html"]
        template_css: str
        template_html: int
        template_variables: Dict[str, Any]
        dependencies: Dict[str, Any]
        format: Literal["html", "pdf", "plaintext"]
        debug: bool

    class InputSerializer(Serializer[InputRequest]):
        template_md = CharField()
        type = CharField()
        template_css = CharField(allow_blank=True, required=False)
        template_html = IntegerField(allow_null=True, required=False)
        template_variables = JSONField()
        dependencies = JSONField()
        format = ChoiceField(choices=["html", "pdf", "plaintext"])
        debug = BooleanField(default=False)

    def post(self, request: Request) -> Union[FileResponse, Response]:
        try:
            report_data = self._parse_and_validate_request_data(request.data)
            html_report, variables = generate_html(
                template=report_data["template_md"],
                template_type=report_data["type"],
                css=report_data.get("template_css", ""),
                html_template=report_data.get("template_html"),
                variables=report_data["template_variables"],
                dependencies=report_data["dependencies"],
            )

            if report_data["debug"]:
                return self._process_debug_response(html_report, variables)
            return self._generate_response_based_on_format(
                html_report, report_data["format"]
            )
        except TemplateError as error:
            return self._handle_template_error(error)
        except Exception as error:
            return notify_error(str(error))

    def _parse_and_validate_request_data(self, data: Dict[str, Any]) -> Any:
        serializer = self.InputSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def _process_debug_response(
        self, html_report: str, variables: Dict[str, Any]
    ) -> Response:
        if variables:
            from django.forms.models import model_to_dict

            # serialize any model instances provided
            for model_name in ("agent", "site", "client"):
                if model_name in variables:
                    model_instance = variables[model_name]
                    serialized_model = model_to_dict(
                        model_instance,
                        fields=[field.name for field in model_instance._meta.fields],
                    )
                    variables[model_name] = serialized_model

        return Response({"template": html_report, "variables": variables})

    def _generate_response_based_on_format(
        self, html_report: str, format: Literal["html", "pdf", "plaintext"]
    ) -> Union[Response, FileResponse]:
        html_report = normalize_asset_url(html_report, format)

        if format != "pdf":
            return Response(html_report)
        else:
            pdf_bytes = generate_pdf(html=html_report)
            return FileResponse(
                ContentFile(pdf_bytes),
                content_type="application/pdf",
                filename="preview.pdf",
            )

    def _handle_template_error(self, error: TemplateError) -> Response:
        if hasattr(error, "lineno"):
            error_message = f"Line {error.lineno}: {error.message}"
        else:
            error_message = str(error)

        return notify_error(error_message)


class ExportReportTemplate(APIView):
    permission_classes = [IsAuthenticated, GenerateReportPerms]

    def post(self, request: Request, pk: int) -> Response:
        template = get_object_or_404(ReportTemplate, pk=pk)

        template_html = template.template_html or None

        base_template = None
        if template_html:
            base_template = {
                "name": template_html.name,
                "html": template_html.html,
            }

        assets = base64_encode_assets(
            template.template_md + base_template["html"]
            if base_template
            else template.template_md
        )
        return Response(
            {
                "base_template": base_template,
                "template": {
                    "name": template.name,
                    "template_css": template.template_css,
                    "template_md": template.template_md,
                    "type": template.type,
                    "depends_on": template.depends_on,
                    "template_variables": template.template_variables,
                },
                "assets": assets,
            }
        )


class ImportReportTemplate(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        try:
            template_obj = json.loads(request.data["template"])
            overwrite = request.data.get("overwrite", False)

            # import base template if exists
            base_template_id = _import_base_template(
                template_obj.get("base_template"), overwrite
            )

            # import template if exists
            report_template = _import_report_template(
                template_obj.get("template"), base_template_id, overwrite
            )

            # import assets if exists
            _import_assets(template_obj.get("assets"))

            return Response(ReportTemplateSerializer(report_template).data)

        except Exception as e:
            # rollback db transaction if any exception occurs
            transaction.set_rollback(True)
            return notify_error(str(e))


class GetAllowedValues(APIView):
    permission_classes = [IsAuthenticated, GenerateReportPerms]

    def post(self, request: Request) -> Response:
        variables = request.data.get("variables", None)
        if variables is None:
            return notify_error("'variables' is required")

        dependencies = request.data.get("dependencies", None)

        # process variables and dependencies
        variables = prep_variables_for_template(
            variables=variables,
            dependencies=dependencies,
            limit_query_results=1,  # only get first item for querysets
        )

        if variables:
            return Response(self._get_dot_notation(variables))

        return Response()

    # recursive function to get properties on any embedded objects
    def _get_dot_notation(
        self, d: Dict[str, Any], parent_key: str = "", path: Optional[str] = None
    ) -> Dict[str, Any]:
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items[new_key] = "Object"
                items.update(self._get_dot_notation(v, new_key, path=path))
            elif isinstance(v, list) or type(v).__name__ == "PermissionQuerySet":
                items[new_key] = f"Array ({len(v)} Results)"
                if v:  # Ensure the list is not empty
                    item = v[0]
                    if isinstance(item, dict):
                        items.update(
                            self._get_dot_notation(item, f"{new_key}[0]", path=path)
                        )
                    else:
                        items[f"{new_key}[0]"] = type(item).__name__

            else:
                items[new_key] = type(v).__name__
        return items


class SharedTemplatesRepo(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def get(self, request: Request) -> Response:
        try:
            url = "https://raw.githubusercontent.com/amidaware/reporting-templates/master/index.json"
            response = requests.get(url, timeout=15)
            files = response.json()
            return Response(
                [
                    {"name": file["name"], "url": file["download_url"]}
                    for file in files
                    if file["download_url"]
                ]
            )
        except Exception as e:
            return notify_error(str(e))

    @transaction.atomic
    def post(self, request: Request) -> Response:
        overwrite = request.data.get("overwrite", False)
        templates = request.data.get("templates", None)

        if not templates:
            return notify_error("No templates to import")

        try:
            for template in templates:
                response = requests.get(template["url"], timeout=10)
                template_obj = response.json()

                # import base template if exists
                base_template_id = _import_base_template(
                    template_obj.get("base_template"), overwrite
                )

                # import template if exists
                _import_report_template(
                    template_obj.get("template"), base_template_id, overwrite
                )

                # import assets if exists
                _import_assets(template_obj.get("assets"))

            return Response()

        except Exception as e:
            # rollback db transaction if any exception occurs
            transaction.set_rollback(True)
            return notify_error(str(e))


class GetReportAssets(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def get(self, request: Request) -> Response:
        path = request.query_params.get("path", "").lstrip("/")

        try:
            directories, files = report_assets_fs.listdir(path)
        except FileNotFoundError:
            return notify_error("The path is invalid")

        response = []

        # parse directories
        for foldername in directories:
            relpath = os.path.join(path, foldername)
            response.append(
                {
                    "name": foldername,
                    "path": relpath,
                    "type": "folder",
                    "size": None,
                    "url": report_assets_fs.url(relpath),
                }
            )

        # parse files
        for filename in files:
            relpath = os.path.join(path, filename)
            response.append(
                {
                    "name": filename,
                    "path": relpath,
                    "type": "file",
                    "size": str(report_assets_fs.size(relpath)),
                    "url": report_assets_fs.url(relpath),
                }
            )

        return Response(response)


class GetAllAssets(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def get(self, request: Request) -> Response:
        only_folders = request.query_params.get("onlyFolders", None)
        only_folders = True if only_folders and only_folders == "true" else False

        try:
            os.chdir(report_assets_fs.base_location)
            response = [self._walk_folder_and_return_node(".", only_folders)]
            return Response(response)
        except FileNotFoundError:
            return notify_error("Unable to process request")

    # TODO: define a Type for file node
    def _walk_folder_and_return_node(self, path: str, only_folders: bool = False):
        # pull report assets from the database so we can pair with the file system assets
        assets = ReportAsset.objects.all()

        for current_dir, subdirs, files in os.walk(path):
            current_dir = "Report Assets" if current_dir == "." else current_dir
            node = {
                "type": "folder",
                "name": current_dir.replace("./", ""),
                "path": path.replace("./", ""),
                "children": [],
                "selectable": False,
                "icon": "folder",
                "iconColor": "yellow-9",
            }
            for dirname in subdirs:
                dirpath = f"{path}/{dirname}"
                node["children"].append(
                    # recursively call
                    self._walk_folder_and_return_node(dirpath, only_folders)
                )

            if not only_folders:
                for filename in files:
                    path = f"{current_dir}/{filename}".replace("./", "").replace(
                        "Report Assets/", ""
                    )
                    try:
                        # need to remove the relative path
                        id = assets.get(file=path).id
                        node["children"].append(
                            {
                                "id": id,
                                "type": "file",
                                "name": filename,
                                "path": path,
                                "icon": "description",
                            }
                        )
                    except ReportAsset.DoesNotExist:
                        pass

            return node


class RenameReportAsset(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    class InputRequest:
        path: str
        newName: str

    class InputSerializer(Serializer[InputRequest]):
        path = CharField(required=True, validators=[path_exists])
        newName = CharField(required=True)

    def put(self, request: Request) -> Response:
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_path = serializer.data["path"]
        new_name = serializer.data["newName"]

        # make sure absolute path isn't processed
        old_path = old_path.lstrip("/") if old_path else ""

        try:
            name = report_assets_fs.rename(path=old_path, new_name=new_name)

            if report_assets_fs.isfile(path=name):
                asset = ReportAsset.objects.get(file=old_path)
                asset.file.name = name
                asset.save()

            return Response(name)
        except OSError as error:
            return notify_error(str(error))
        except SuspiciousFileOperation as error:
            return notify_error(str(error))


class CreateAssetFolder(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def post(self, request: Request) -> Response:
        path = request.data["path"].lstrip("/") if "path" in request.data else ""

        if not path:
            return notify_error("'path' in required.")
        try:
            new_path = report_assets_fs.createfolder(path=path)
            return Response(new_path)
        except OSError as error:
            return notify_error(str(error))
        except SuspiciousFileOperation as error:
            return notify_error(str(error))


class DeleteAssets(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    class InputRequest:
        paths: List[str]

    class InputSerializer(Serializer[InputRequest]):
        paths = ListField(required=True)

    def post(self, request: Request) -> Response:
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        paths = serializer.data["paths"]

        try:
            for path in paths:
                path = path.lstrip("/") if path else ""
                if report_assets_fs.isdir(path=path):
                    shutil.rmtree(report_assets_fs.path(path))
                    ReportAsset.objects.filter(file__startswith=f"{path}/").delete()
                else:
                    try:
                        asset = ReportAsset.objects.get(file=path)
                        asset.file.delete()
                        asset.delete()
                    except ObjectDoesNotExist:
                        report_assets_fs.delete(path)

            return Response()

        except OSError as error:
            return notify_error(str(error))
        except SuspiciousFileOperation as error:
            return notify_error(str(error))


class UploadAssets(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def post(self, request: Request) -> Response:
        path = (
            request.data["parentPath"].lstrip("/")
            if "parentPath" in request.data
            else ""
        )

        try:
            response = {}

            # make sure this is actually a directory
            if report_assets_fs.isdir(path=path):
                for filename in request.FILES:
                    asset = ReportAsset(file=request.FILES[filename])
                    asset.file.name = os.path.join(path, filename)
                    asset.save()

                    asset.refresh_from_db()

                    response[filename] = {
                        "id": asset.id,
                        "filename": asset.file.name,
                    }

                return Response(response)
            else:
                return notify_error("parentPath doesn't point to a directory")

        except OSError as error:
            return notify_error(str(error))
        except SuspiciousFileOperation as error:
            return notify_error(str(error))


class DownloadAssets(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def get(self, request: Request) -> Union[Response, FileResponse]:
        path = request.query_params.get("path", "")

        # make sure absolute path isn't processed
        path = path.lstrip("/") if path else ""

        try:
            full_path = report_assets_fs.path(name=path)
            if report_assets_fs.isdir(path=path):
                zip_path = shutil.make_archive(
                    base_name=f"{report_assets_fs.path(name=path)}.zip",
                    format="zip",
                    root_dir=full_path,
                )

                response = FileResponse(
                    open(zip_path, "rb"),
                    as_attachment=True,
                    filename=zip_path.split("/")[-1],
                )

                os.remove(zip_path)

                return response
            else:
                return FileResponse(
                    open(full_path, "rb"),
                    as_attachment=True,
                    filename=full_path.split("/")[-1],
                )

        except OSError as error:
            return notify_error(str(error))
        except SuspiciousFileOperation as error:
            return notify_error(str(error))


class MoveAssets(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    class InputRequest:
        srcPaths: List[str]
        destination: str

    class InputSerializer(Serializer[InputRequest]):
        srcPaths = ListField(required=True)
        destination = CharField(required=True, validators=[path_exists])

    def post(self, request: Request) -> Response:
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        paths = serializer.data["srcPaths"]
        destination = serializer.data["destination"]

        try:
            response = {}
            for path in paths:
                new_path = report_assets_fs.move(source=path, destination=destination)

                response["path"] = new_path

            return Response(response)

        except OSError as error:
            return notify_error(str(error))
        except SuspiciousFileOperation as error:
            return notify_error(str(error))


class ReportHTMLTemplateSerializer(ModelSerializer[ReportHTMLTemplate]):
    class Meta:
        model = ReportHTMLTemplate
        fields = "__all__"


class GetAddReportHTMLTemplate(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def get(self, request: Request) -> Response:
        reports = ReportHTMLTemplate.objects.all()
        return Response(ReportHTMLTemplateSerializer(reports, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = ReportHTMLTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save()

        return Response(ReportHTMLTemplateSerializer(response).data)


class GetEditDeleteReportHTMLTemplate(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def get(self, request: Request, pk: int) -> Response:
        template = get_object_or_404(ReportHTMLTemplate, pk=pk)

        return Response(ReportHTMLTemplateSerializer(template).data)

    def put(self, request: Request, pk: int) -> Response:
        template = get_object_or_404(ReportHTMLTemplate, pk=pk)

        serializer = ReportHTMLTemplateSerializer(
            instance=template, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        response = serializer.save()

        return Response(ReportHTMLTemplateSerializer(response).data)

    def delete(self, request: Request, pk: int) -> Response:
        get_object_or_404(ReportHTMLTemplate, pk=pk).delete()

        return Response()


class ReportDataQuerySerializer(ModelSerializer[ReportDataQuery]):
    class Meta:
        model = ReportDataQuery
        fields = "__all__"


class GetAddReportDataQuery(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def get(self, request: Request) -> Response:
        reports = ReportDataQuery.objects.all()
        return Response(ReportDataQuerySerializer(reports, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = ReportDataQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = serializer.save()

        return Response(ReportDataQuerySerializer(response).data)


class GetEditDeleteReportDataQuery(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def get(self, request: Request, pk: int) -> Response:
        template = get_object_or_404(ReportDataQuery, pk=pk)

        return Response(ReportDataQuerySerializer(template).data)

    def put(self, request: Request, pk: int) -> Response:
        template = get_object_or_404(ReportDataQuery, pk=pk)

        serializer = ReportDataQuerySerializer(
            instance=template, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        response = serializer.save()

        return Response(ReportDataQuerySerializer(response).data)

    def delete(self, request: Request, pk: int) -> Response:
        get_object_or_404(ReportDataQuery, pk=pk).delete()

        return Response()


class NginxRedirect(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request, path: str) -> HttpResponse:
        id = request.query_params.get("id", "")
        try:
            asset_uuid = uuid.UUID(id, version=4)
            asset = get_object_or_404(ReportAsset, id=asset_uuid)
            new_path = path.split("?")[0]
            if asset.file.name == new_path:
                response = HttpResponse(status=200)
                response["X-Accel-Redirect"] = "/assets/" + new_path
                return response
            else:
                raise PermissionDenied()
        except ValueError:
            return notify_error("There was a error processing the request")


class QuerySchema(APIView):
    permission_classes = [IsAuthenticated, ReportingPerms]

    def get(self, request):
        schema_path = "static/reporting/schemas/query_schema.json"

        try:
            with open(djangosettings.BASE_DIR / schema_path, "r") as f:
                data = json.load(f)

            return JsonResponse(data)
        except FileNotFoundError:
            return notify_error("There was an error getting the file")
