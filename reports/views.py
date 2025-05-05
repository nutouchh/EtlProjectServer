import os
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from django.conf import settings
from django.core.files.storage import default_storage
from .models import ReportInfo, SystemLog
from .serializers import ReportInfoSerializer, SystemLogsSerializer
from reports.etl.pipeline import run_pipeline
from rest_framework.generics import CreateAPIView
from .serializers import UploadReportSerializer
from rest_framework.permissions import IsAuthenticated
from django.core.files.storage import default_storage
from django.utils.text import slugify
from uuid import uuid4

class UploadReportView(CreateAPIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]
    serializer_class = UploadReportSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data['file']
        distributor = request.data.get('distributor')
        month = request.data.get('month').split("-")[1]
        f_name = f"{distributor}-{month}"

        filename = f"{uuid4().hex}_{file.name}"
        s3_path = f"uploads_{month}/{filename}"

        saved_path = default_storage.save(s3_path, file)

        tmp_dir = os.path.join(settings.BASE_DIR, 'temp_media')
        os.makedirs(tmp_dir, exist_ok=True)

        tmp_path = os.path.join(tmp_dir, file.name)
        with open(tmp_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        report = ReportInfo.objects.create(
            s3_uri=saved_path,
            file_name=f_name,
            status='queued',
            user=request.user
        )

        run_pipeline(tmp_path, report.id, distributor, month)

        return Response({"report_id": report.id}, status=status.HTTP_201_CREATED)



class ReportListView(generics.ListAPIView):
    serializer_class = ReportInfoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'tech':
            return ReportInfo.objects.all().order_by('-created_at')
        return ReportInfo.objects.filter(user=user).order_by('-created_at')

class SystemLogListView(generics.ListAPIView):
    serializer_class = SystemLogsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'tech':
            return SystemLog.objects.all().order_by('-timestamp')
        return SystemLog.objects.filter(report__user=user).order_by('-timestamp')