from reports.models import SystemLog

def log_to_db(report_id, message, step='other', log_level='info', details=None):
    SystemLog.objects.create(
        report_id=report_id,
        message=message,
        step=step,
        log_level=log_level,
        details=details
    )
