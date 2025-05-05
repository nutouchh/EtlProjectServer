from django.db import models
from django.conf import settings

class ReportInfo(models.Model):
    STATUS_CHOICES = (
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
    )

    s3_uri = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_DEFAULT , related_name='reports',blank=True,default=1)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    details = models.TextField(blank=True, null=True)


class SystemLog(models.Model):
    LOG_LVL = (
        ('info', 'Info'),
        ('error', 'Error')
    )

    STEP = (
        ('extract', 'Extract'),
        ('transform', 'Transform'),
        ('load', 'Load'),
        ('other', 'Other'),
    )

    report = models.ForeignKey(ReportInfo, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    log_level = models.CharField(max_length=50, choices=LOG_LVL, default='info')
    step = models.CharField(max_length=50, choices=STEP, default='other')
    message = models.TextField()
    details = models.TextField(blank=True, null=True)
