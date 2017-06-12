import behave

import pendulum

from share import models
from share import tasks


@behave.given('{label} is allowed to be backharvested')
def allow_backharvesting(context, label):
    models.SourceConfig.objects.filter(label=label).update(full_harvest=True)


@behave.given('{label}\'s earliest record is {date}')
def set_earliest_record(context, label, date):
    models.SourceConfig.objects.filter(label=label).update(earliest_date=date)


@behave.given('a {status} harvest of {label}')
@behave.given('the last harvest of {label} was {end}')
@behave.given('a {status} harvest of {label} for {start} to {end}')
def make_harvest_job(context, label, status='succeeded', start=None, end=None):
    source_config = models.SourceConfig.objects.get(label=label)

    if end:
        end = pendulum.parse(end)

    if start:
        start = pendulum.parse(start)

    if end and not start:
        start = end - source_config.harvest_interval

    models.HarvestJob.objects.create(
        completions=1,
        end_date=end,
        start_date=start,
        status=getattr(models.HarvestJob.STATUS, status),
        source_config=source_config,
        source_config_version=source_config.version,
        harvester_version=models.Harvester.objects.get(sourceconfig__label=label).version,
    )


@behave.when('harvests are scheduled at {time} on {date}')
@behave.when('harvests are scheduled on {date}')
def schedule_harvests(context, date, time='00:00'):
    tasks.schedule_harvests(cutoff=pendulum.parse('{}T{}+00:00'.format(date, time)))


@behave.then('{label} will have {number} harvest job')
@behave.then('{label} will have {number} harvest jobs')
@behave.then('{label} will have {number} harvest job for {start} to {end}')
@behave.then('{label} will have {number} harvest jobs for {start} to {end}')
def assert_num_harvest_jobs(context, label, number, start=None, end=None):
    qs = models.HarvestJob.objects.filter(source_config__label=label)

    if start:
        qs = qs.filter(start_date=start)

    if end:
        qs = qs.filter(end_date=end)

    assert qs.count() == int(number), '{!r} has {} jobs not {}'.format(models.SourceConfig.objects.get(label=label), qs.count(), number)


@behave.then('{label}\'s latest harvest job\'s {field} will be {value}')
def assert_latest_harvestjob_value(context, label, field, value):
    context.subject = job = models.HarvestJob.objects.filter(
        source_config__label=label
    ).first()

    if field == 'status':
        value = getattr(models.HarvestJob.STATUS, value)

    assert getattr(job, field) == value, '{!r}.{} ({!r}) != {!r}'.format(job, field, getattr(job, field), value)
