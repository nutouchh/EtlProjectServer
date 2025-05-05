from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from reports.etl.pipeline import run_pipeline
import tempfile
import os
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from reports.models import ReportInfo, SystemLog


class UploadReportTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='test', password='testpass')
        self.client.force_authenticate(self.user)

    def test_upload_valid_report(self):
        file = SimpleUploadedFile("test.csv", b"col1,col2\nval1,val2", content_type="text/csv")
        response = self.client.post(
            '/api/upload_report/',
            {
                'file': file,
                'distributor': 'ООО Дистрибьютор',
                'month': '2024-04'
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('report_id', response.data)

    def test_upload_without_file(self):
        response = self.client.post(
            '/api/upload_report/',
            {
                'distributor': 'Без файла',
                'month': '2024-04'
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PipelineTest(TestCase):
    def setUp(self):
        # Создаём пользователя
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass')

        # Создаём ReportInfo
        self.report = ReportInfo.objects.create(
            s3_uri='dummy.csv',
            file_name='dummy.csv',
            status='queued',
            user=self.user
        )

        # Создаём временный CSV-файл
        self.test_file = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.csv')
        self.test_file.write("product,price\napple,10\nbanana,20")
        self.test_file.seek(0)

    def tearDown(self):
        # Закрываем и удаляем временный файл
        self.test_file.close()
        os.unlink(self.test_file.name)

    def test_pipeline_creates_logs(self):
        run_pipeline(
            self.test_file.name,
            self.report.id,
            distr='ООО ТестДистрибьютор',
            month='2024-04'
        )
        logs = SystemLog.objects.filter(report=self.report)
        self.assertTrue(logs.exists(), "Логи должны быть созданы после запуска pipeline.")

    def test_pipeline_with_invalid_file(self):
        with tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.csv') as bad_file:
            bad_file.write(";;;")  # кривой CSV
            bad_file_path = bad_file.name

        run_pipeline(bad_file_path, self.report.id, distr='Ошибочный', month='2024-04')
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'error')




class ViewAccessTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='manager', password='1234', role='manager')
        self.tech = get_user_model().objects.create_user(username='tech', password='1234', role='tech')

    def test_reports_only_self(self):
        ReportInfo.objects.create(user=self.user, file_name='f1', status='done')
        ReportInfo.objects.create(user=self.tech, file_name='f2', status='done')

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/reports/')
        self.assertEqual(len(response.data), 1)

    def test_logs_only_own_reports(self):
        r1 = ReportInfo.objects.create(user=self.user, file_name='r1.csv', status='done')
        r2 = ReportInfo.objects.create(user=self.tech, file_name='r2.csv', status='done')

        SystemLog.objects.create(report=r1, step='extract', message='msg')
        SystemLog.objects.create(report=r2, step='load', message='msg')

        self.client.force_authenticate(self.user)
        response = self.client.get('/api/logs/')
        self.assertEqual(len(response.data), 1)

    def test_tech_sees_all_logs(self):
        r1 = ReportInfo.objects.create(user=self.user, file_name='r1.csv', status='done')
        r2 = ReportInfo.objects.create(user=self.tech, file_name='r2.csv', status='done')

        SystemLog.objects.create(report=r1, step='extract', message='msg')
        SystemLog.objects.create(report=r2, step='load', message='msg')

        self.client.force_authenticate(self.tech)
        response = self.client.get('/api/logs/')
        self.assertEqual(len(response.data), 2)

    def test_logs_not_accessible_unauthenticated(self):
        response = self.client.get('/api/logs/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='modeltestuser', password='test123')

    def test_report_info_str_fields(self):
        report = ReportInfo.objects.create(
            file_name='test.csv',
            s3_uri='test.csv',
            status='done',
            user=self.user
        )
        self.assertEqual(report.status, 'done')

    def test_system_log_creation(self):
        report = ReportInfo.objects.create(
            file_name='test.csv',
            s3_uri='test.csv',
            status='done',
            user=self.user
        )
        log = SystemLog.objects.create(report=report, message='Test', step='load')
        self.assertEqual(log.step, 'load')
        self.assertEqual(log.message, 'Test')

    def test_system_log_auto_timestamp(self):
        report = ReportInfo.objects.create(
            file_name='log.csv',
            s3_uri='log.csv',
            status='queued',
            user=self.user
        )
        log = SystemLog.objects.create(report=report, message='Создан', step='extract')
        self.assertIsNotNone(log.timestamp)


class RoleAccessTest(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(username='manager', password='1234', role='manager')
        self.tech = User.objects.create_user(username='tech', password='1234', role='tech')

        self.report1 = ReportInfo.objects.create(
            file_name='rep1.csv',
            s3_uri='rep1.csv',
            status='done',
            user=self.manager
        )
        self.report2 = ReportInfo.objects.create(
            file_name='rep2.csv',
            s3_uri='rep2.csv',
            status='done',
            user=self.tech
        )

        self.log1 = SystemLog.objects.create(
            report=self.report1, message='log1', step='extract'
        )
        self.log2 = SystemLog.objects.create(
            report=self.report2, message='log2', step='load'
        )

    def test_manager_sees_only_own_reports(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get('/api/reports/')
        ids = [r['id'] for r in response.json()]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ids, [self.report1.id])

    def test_tech_sees_all_reports(self):
        self.client.force_authenticate(self.tech)
        response = self.client.get('/api/reports/')
        ids = sorted([r['id'] for r in response.json()])
        expected = sorted([self.report1.id, self.report2.id])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ids, expected)

    def test_manager_sees_only_own_logs(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get('/api/logs/')
        log_ids = [log['id'] for log in response.json()]
        self.assertEqual(log_ids, [self.log1.id])

    def test_tech_sees_all_logs(self):
        self.client.force_authenticate(self.tech)
        response = self.client.get('/api/logs/')
        log_ids = sorted([log['id'] for log in response.json()])
        expected = sorted([self.log1.id, self.log2.id])
        self.assertEqual(log_ids, expected)



