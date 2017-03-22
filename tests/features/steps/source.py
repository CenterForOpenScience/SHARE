import behave

from share import models
from share import tasks

from tests import factories


@behave.given('the source {name}')
def make_source(context, name):
    if not hasattr(context, 'source'):
        context.sources = {}
    context.sources[name] = factories.SourceFactory(name=name)
    context.subject = ('sources', context.sources[name])


@behave.given('{name} has a source config, {label}')
def make_source_config(context, name, label):
    factories.SourceConfigFactory(label=label, source=models.Source.objects.get(name=name))


@behave.given('a {status} harvest of {label}')
@behave.given('a {status} harvest of {label} for {start} to {end}')
def make_harvest_log(context, status, label, start=None, end=None):
    start, end = tasks.HarvesterTask.resolve_date_range(start, end)
    models.HarvestLog.objects.create(
        completions=1,
        end_date=end,
        start_date=start,
        status=getattr(models.HarvestLog.STATUS, status),
        source_config=models.SourceConfig.objects.get(label=label),
        source_config_version=models.SourceConfig.objects.get(label=label).version,
        harvester_version=models.Harvester.objects.get(sourceconfig__label=label).version,
    )


@behave.given('{label} is updated to version {version}')
def update_harvester(context, label, version):
    models.Harvester.objects.get(sourceconfig__label=label).get_class().VERSION = int(version)


@behave.when('{label} is harvested')
@behave.when('{label} is harvested for {start} to {end}')
def start_harvest(context, label, start=None, end=None):
    tasks.HarvesterTask().apply((1, label), {'start': start, 'end': end}, retries=99999999999)


@behave.then('{label} will have {number} harvest log')
@behave.then('{label} will have {number} harvest logs')
@behave.then('{label} will have {number} harvest log for {start} to {end}')
@behave.then('{label} will have {number} harvest logs for {start} to {end}')
def assert_num_harvest_logs(context, label, number, start=None, end=None):
    qs = models.HarvestLog.objects.filter(source_config__label=label)

    if start:
        qs = qs.filter(start_date=start)

    if end:
        qs = qs.filter(end_date=end)

    assert qs.count() == int(number), '{!r} has {} logs not {}'.format(models.SourceConfig.objects.get(label=label), qs.count(), number)


@behave.then('{label}\'s latest harvest log\'s {field} will be {value}')
def assert_latest_harvestlog_value(context, label, field, value):
    context.subject = log = models.HarvestLog.objects.filter(
        source_config__label=label
    ).first()

    if field == 'status':
        value = getattr(models.HarvestLog.STATUS, value)

    assert getattr(log, field) == value, '{!r}.{} ({!r}) != {!r}'.format(log, field, getattr(log, field), value)


@behave.then('it\'s {field} will be {value}')
def assert_subject_value(context, field, value):
    assert hasattr(context, 'subject'), 'No subject has been set, don\'t use pronouns!'
    assert hasattr(context.subject, field), '{!r} has not attribute {!r}'.format(context.subject, field)

    if hasattr(context.subject, 'refresh_from_db'):
        context.subject.refresh_from_db()
    assert getattr(context.subject, field) == value, '{!r}.{} ({!r}) != {!r}'.format(context.subject, field, getattr(context.subject, field), value)


@behave.then('it will be completed {number} time')
@behave.then('it will be completed {number} times')
def assert_subject_completions(context, number):
    assert_subject_value(context, 'completions', int(number))
    # assert hasattr(context.subject, 'completions')
    # # context.subject.refresh_from_db()
    # assert context.subject.completions == int(number), '{!r}.{} ({!r}) != {!r}'.format(context.subject, 'completions)
