from rest_framework import serializers
from .models import ReportInfo, SystemLog


class ReportInfoSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ReportInfo
        fields = ['id', 's3_uri', 'file_name', 'status', 'created_at', 'updated_at', 'details', 'username']


class SystemLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemLog
        fields = ['id', 'report', 'timestamp', 'log_level', 'step', 'message', 'details']


class UploadReportSerializer(serializers.Serializer):
    file = serializers.FileField()