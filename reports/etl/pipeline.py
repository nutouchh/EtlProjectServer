from django.utils import timezone

from reports.etl.extractors.extractors import ExcelExtractor, OldExcelExtractor, CSVExtractor
from reports.etl.loaders.loader import Loader
from reports.etl.logger import log_to_db
from reports.etl.transformers.transformers import Transformer
import tracemalloc
import time
import psutil
import os

from reports.models import ReportInfo


def run_pipeline(local_path, report_id, distr, month):
    try:
        # process = psutil.Process(os.getpid())
        # start_mem = process.memory_info().rss
        #
        # start = time.perf_counter()

        log_to_db(report_id, 'Запуск обработки файла')

        if local_path.endswith(".xlsx") :
            log_to_db(report_id, 'Начало извлечения .xlsx', step='extract')
            extractor = ExcelExtractor()
        elif local_path.endswith(".xls"):
            log_to_db(report_id, 'Начало извлечения .xls', step='extract')
            extractor = OldExcelExtractor()
        elif local_path.endswith(".csv"):
            log_to_db(report_id, 'Начало извлечения .csv', step='extract')
            extractor = CSVExtractor()
        else:
            log_to_db(report_id, 'Расширение не соответствует требованиям', step='extract', log_level='error',
                      details=ValueError("Unsupported file format"))
            raise ValueError("Unsupported file format")

        df = extractor.extract(local_path)

        ReportInfo.objects.filter(id=report_id).update(status='processing', updated_at=timezone.now())

        log_to_db(report_id, 'Начало трансформации файла', step='transform')
        transformer = Transformer()
        transformed_df = transformer.transform(df, distr, month)
        log_to_db(report_id, 'Трансформация завершена, получен DF', step='transform')

        log_to_db(report_id, 'Начало загрузки отчета в БД', step='load')
        loader = Loader()
        loader.load(transformed_df)

        # end = time.perf_counter()
        #
        # end_mem = process.memory_info().rss
        # used_mb = (end_mem - start_mem) / 1024 / 1024
        #
        # print(f"ETL использовал: {used_mb:.2f} MB за {end - start:.2f} сек")

        log_to_db(report_id, 'Загрузка отчета в БД завершена', step='load')

        ReportInfo.objects.filter(id=report_id).update(status='done', updated_at=timezone.now())
        log_to_db(report_id, f'Загрузка отчета {report_id} завершена')
    except Exception as e:
        error_type = type(e).__name__
        ReportInfo.objects.filter(id=report_id).update(
            status='error',
            details=f'{error_type}: {str(e)}',
            updated_at = timezone.now()
        )
        log_to_db(report_id, 'Обработка отчета прервана исключением', log_level='error', details=f'{error_type}: {str(e)}',)