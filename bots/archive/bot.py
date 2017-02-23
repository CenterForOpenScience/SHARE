import datetime
import bz2
import io
import logging

import boto3
import botocore

from django.db import transaction
from django.conf import settings
from django.core.paginator import Paginator
from django.core import serializers

from share.bot import Bot
from share.models import CeleryProviderTask

logger = logging.getLogger(__name__)


def get_bucket(bucket_name):
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


def queryset_to_compressed_json(queryset, model):
    compressed_output = io.BytesIO()
    output = io.StringIO(serializers.serialize('json', queryset))
    compressed_output.write(bz2.compress(str.encode(output.getvalue())))

    return compressed_output


def put_s3(bucket, location, data):
    s3 = boto3.resource('s3')
    current_date = datetime.datetime.utcnow().isoformat()
    top_level_folder = settings.CELERY_TASK_FOLDER_NAME + '/' if settings.CELERY_TASK_FOLDER_NAME else ''
    try:
        s3.Object(bucket, top_level_folder + location + current_date + '.json.bz2').put(
            Body=data.getvalue(),
            ServerSideEncryption='AES256'
        )
    except botocore.exceptions.ClientError as e:
        raise botocore.exceptions.ClientError(e)


def delete_queryset(queryset):
    num_deleted = 0
    try:
        with transaction.atomic():
            num_deleted, deleted_metadata = queryset.delete()
    except Exception as e:
        logger.exception('Failed to delete queryset with exception %s', e)
        raise

    logger.info('Deleted %s CeleryTasks', num_deleted)


class ArchiveBot(Bot):

    def run(self, chunk_size=5000):

        # require storage and folder settings on prod and staging
        if settings.DEBUG is False:
            if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
                raise Exception('No storage found! CeleryTasks will NOT be archived or deleted.')
            if not settings.CELERY_TASK_FOLDER_NAME:
                raise Exception('Folder name not set! Please define folder name in project.settings')

        self.bucket = ''
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            logger.warning('No storage found! CeleryTasks will NOT be archived but WILL be deleted.')
        else:
            if not settings.CELERY_TASK_BUCKET_NAME:
                raise Exception('Bucket name not set! Please define bucket name in project.settings')
            self.bucket = get_bucket(settings.CELERY_TASK_BUCKET_NAME)

        logger.info('%s started converting queryset to json data', self.started_by)

        self.chunk_size = chunk_size

        current_time = datetime.datetime.utcnow()
        one_day = datetime.timedelta(days=-1)
        one_week = datetime.timedelta(weeks=-1)
        two_weeks = datetime.timedelta(weeks=-2)

        # bots.elasticsearch (24hrs)
        elasticsearch_tasks = CeleryProviderTask.objects.filter(
            app_label='elasticsearch',
            timestamp__lt=current_time + one_day,
            status=3
        )
        # normalizertask (1 week)
        normalizer_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.NormalizerTask',
            timestamp__lt=current_time + one_week,
            status=3
        )
        # disambiguatortask (1 week)
        disambiguator_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.DisambiguatorTask',
            timestamp__lt=current_time + one_week,
            status=3
        )
        # harvestertask (2 weeks)
        harvester_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.HarvesterTask',
            timestamp__lt=current_time + two_weeks,
            status=3
        )
        # archivetask (2 weeks)
        archive_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.ArchiveTask',
            timestamp__lt=current_time + two_weeks,
            status=3
        )

        if elasticsearch_tasks.exists():
            self.paginate_queryset(
                elasticsearch_tasks,
                'elasticsearch/elasticsearch_tasks_',
                'Elasticsearch CeleryTask'
            )

        if normalizer_tasks.exists():
            self.paginate_queryset(
                normalizer_tasks,
                'normalizer/normalizer_tasks_',
                'NormalizerTask'
            )

        if disambiguator_tasks.exists():
            self.paginate_queryset(
                disambiguator_tasks,
                'disambiguator/disambiguator_tasks_',
                'DisambiguatorTask'
            )

        if harvester_tasks.exists():
            self.paginate_queryset(
                harvester_tasks,
                'harvester/harvester_tasks_',
                'HarvesterTask'
            )

        if archive_tasks.exists():
            self.paginate_queryset(
                archive_tasks,
                'archive/archive_tasks_',
                'ArchiveTask'
            )

    def archive_queryset(self, page, model, location, task_name):
        compressed_data = queryset_to_compressed_json(page.object_list, model)
        put_s3(self.bucket, location, compressed_data)
        logger.info('Finished archiving data for %s', task_name)

    def paginate_queryset(self, queryset, location, task_name):
        if self.bucket:
            total = queryset.count()
            logger.info('Found %s %ss eligible for archiving', total, task_name)
            logger.info('Archiving in chunks of %d', self.chunk_size)

            model = queryset.model
            paginator = Paginator(queryset, self.chunk_size)
            page = paginator.page(1)
            self.archive_queryset(page, model, location, task_name)

            while page.has_next():
                page = paginator.page(page.next_page_number())
                self.archive_queryset(page, model, location, task_name)
                logger.info('Archived %d of %d', page.end_index(), total)

        delete_queryset(queryset)
