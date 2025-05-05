from django.urls import path, include

from reports.views import UploadReportView, ReportListView, SystemLogListView

urlpatterns = [
    path('upload_report/', UploadReportView.as_view(), name='upload-report') ,
    path('reports/', ReportListView.as_view()),
    path('logs/', SystemLogListView.as_view()),
]
