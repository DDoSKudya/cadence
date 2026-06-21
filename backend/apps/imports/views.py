from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.imports.models import ImportLog
from apps.imports.selectors import get_import_log, list_import_logs
from apps.imports.serializers import ImportLogSerializer
from apps.imports.services import JsonImportService
from apps.imports.validators import ImportValidationError


class ImportListView(APIView):
    def get(self, request):
        logs = list_import_logs()
        return Response(ImportLogSerializer(logs, many=True).data)


class ImportDetailView(APIView):
    def get(self, request, pk: int):
        import_log = get_import_log(pk)
        return Response(ImportLogSerializer(import_log).data)


class ImportScanView(APIView):
    def post(self, request):
        processed = JsonImportService.scan_inbox()
        return Response({"processed": processed}, status=status.HTTP_202_ACCEPTED)


class ImportRetryView(APIView):
    def post(self, request, pk: int):
        import_log = get_object_or_404(ImportLog, pk=pk)
        try:
            result = JsonImportService.retry_import(import_log)
        except ImportValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        except FileNotFoundError:
            return Response(
                {"detail": "Import file not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            ImportLogSerializer(result.import_log).data,
            status=status.HTTP_200_OK,
        )
