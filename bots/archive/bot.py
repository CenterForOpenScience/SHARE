import csv
import datetime
import gzip
import io
import logging
import os

import boto3
import botocore

from django.db import transaction
from django.conf import settings

from share.bot import Bot
from share.models import CeleryProviderTask

logger = logging.getLogger(__name__)


class ArchiveBot(Bot):

    def run(self):
        # check for storage settings
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            if os.environ.get('DEBUG', True) is False:
                raise Exception('No storage found! CeleryTasks will NOT be archived or deleted.')
            logger.warning('No storage found! CeleryTasks will NOT be archived but WILL be deleted.')

        logger.info('%s started converting queryset to csv data at %s', self.started_by, datetime.datetime.utcnow().isoformat())

        if not settings.CELERY_TASK_BUCKET_NAME:
            raise Exception('Bucket name not set! Please define bucket name in project.settings')
        bucket = self.get_bucket(settings.CELERY_TASK_BUCKET_NAME)

        current_time = datetime.datetime.utcnow()
        one_day = datetime.timedelta(days=-1)
        one_week = datetime.timedelta(weeks=-1)
        two_weeks = datetime.timedelta(weeks=-2)

        # bots.elasticsearch (24hrs)
        self.elasticsearch_tasks = CeleryProviderTask.objects.filter(
            app_label='elasticsearch',
            timestamp__lt=current_time + one_day
        )
        # normalizertask (1 week)
        self.normalizer_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.NormalizerTask',
            timestamp__lt=current_time + one_week
        )
        # disambiguatortask (1 week)
        self.disambiguator_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.DisambiguatorTask',
            timestamp__lt=current_time + one_week
        )
        # harvestertask (2 weeks)
        self.harvester_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.HarvesterTask',
            timestamp__lt=current_time + two_weeks
        )
        # archivetask (2 weeks)
        self.archive_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.ArchiveTask',
            timestamp__lt=current_time + two_weeks
        )

        if self.elasticsearch_tasks.exists():
            compressed_data = self.queryset_to_compressed_csv(self.elasticsearch_tasks)
            self.put_s3(bucket, 'elasticsearch/elasticsearch_tasks_', compressed_data)

            logger.info('Finished archiving data for Elasticsearch CeleryTask at %s', datetime.datetime.utcnow().isoformat())

            self.delete_queryset(self.elasticsearch_tasks)

        if self.normalizer_tasks.exists():
            compressed_data = self.queryset_to_compressed_csv(self.normalizer_tasks)
            self.put_s3(bucket, 'normalizer/normalizer_tasks_', compressed_data)

            logger.info('Finished archiving data for NormalizerTask at %s', datetime.datetime.utcnow().isoformat())

            self.delete_queryset(self.normalizer_tasks)

        if self.disambiguator_tasks.exists():
            compressed_data = self.queryset_to_compressed_csv(self.disambiguator_tasks)
            self.put_s3(bucket, 'disambiguator/disambiguator_tasks_', compressed_data)

            logger.info('Finished archiving data for DisambiguatorTask at %s', datetime.datetime.utcnow().isoformat())

            self.delete_queryset(self.disambiguator_tasks)

        if self.harvester_tasks.exists():
            compressed_data = self.queryset_to_compressed_csv(self.harvester_tasks)
            self.put_s3(bucket, 'harvester/harvester_tasks_', compressed_data)

            logger.info('Finished archiving data for HarvesterTask at %s', datetime.datetime.utcnow().isoformat())

            self.delete_queryset(self.harvester_tasks)

        if self.archive_tasks.exists():
            compressed_data = self.queryset_to_compressed_csv(self.archive_tasks)
            self.put_s3(bucket, 'archive/archive_tasks_', compressed_data)

            logger.info('Finished archiving data for ArchiveTask at %s', datetime.datetime.utcnow().isoformat())

            self.delete_queryset(self.archive_tasks)

    def queryset_to_compressed_csv(self, queryset):
        model = queryset.model
        compressed_output = io.BytesIO()
        output = io.StringIO()
        writer = csv.writer(output)

        headers = []
        for field in model._meta.fields:
            headers.append(field.name)
        writer.writerow(headers)

        for obj in queryset.iterator():
            row = []
            for field in headers:
                val = getattr(obj, field)
                if callable(val):
                    val = val()
                if isinstance(val, str):
                    val = val.encode("utf-8")
                row.append(val)
            writer.writerow(row)

        with gzip.GzipFile(filename='tmp.gz', mode='wb', fileobj=compressed_output) as f_out:
            f_out.write(str.encode(output.getvalue()))
        return compressed_output

    def get_bucket(self, bucket_name):
        s3 = boto3.resource('s3')
        try:
            s3.meta.client.head_bucket(Bucket=bucket_name)
        except botocore.exceptions.ClientError as e:
            # If a client error is thrown, then check that it was a 404 error.
            # If it was a 404 error, then the bucket does not exist.
            error_code = int(e.response['Error']['Code'])
            if error_code != 404:
                raise botocore.exceptions.ClientError(e)
            s3.create_bucket(Bucket=bucket_name)

        return bucket_name

    def put_s3(self, bucket, location, data):
        s3 = boto3.resource('s3')
        try:
            current_date = datetime.datetime.utcnow().isoformat()
            s3.Object(bucket, location + current_date + '.gz').put(Body=data.getvalue())
        except botocore.exceptions.ClientError as e:
            raise botocore.exceptions.ClientError(e)

    def delete_queryset(self, querySet):
        num_deleted = 0
        try:
            with transaction.atomic():
                num_deleted = querySet.delete()
        except Exception as e:
            raise Exception('Failed to delete queryset with exception %s', e)

        logger.info('Deleted %s CeleryTasks at %s', num_deleted, datetime.datetime.utcnow().isoformat())
