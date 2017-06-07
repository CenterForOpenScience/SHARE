import behave

import pendulum

from share import models
from share import tasks
from share.harvest.scheduler import HarvestScheduler

from tests import factories


@behave.given('the source {name}')
def make_source(context, name):
    if not hasattr(context, 'source'):
        context.sources = {}
    context.sources[name] = factories.SourceFactory(name=name)
    context.subject = ('sources', context.sources[name])


@behave.given('{name} has a source config, {label}')
@behave.given('a source config, {label}, that harvests {interval}')
@behave.given('a source config, {label}, that harvests {interval} after {time}')
def make_source_config(context, label, name=None, interval=None, time=None):
    kwargs = {'label': label}

    if name is None:
        kwargs['source'] = factories.SourceFactory()
    else:
        kwargs['source'] = models.Source.objects.get(name=name)

    if interval is not None:
        kwargs['harvest_interval'] = {
            'daily': '1 day',
            'weekly': '1 week',
            'fortnightly': '2 weeks',
            'yearly': '1 year',
            'monthly': '1 month',
        }[interval]

    if time is not None:
        kwargs['harvest_after'] = time

    factories.SourceConfigFactory(**kwargs)


@behave.given('{label} is updated to version {version}')
def update_harvester(context, label, version):
    models.Harvester.objects.get(sourceconfig__label=label).get_class().VERSION = int(version)


@behave.when('{label} is harvested')
@behave.when('{label} is harvested for {start} to {end}')
def start_harvest(context, label, start=None, end=None):
    log = HarvestScheduler(models.SourceConfig.objects.get(label=label)).range(
        pendulum.parse(start),
        pendulum.parse(end),
    )[0]

    tasks.harvest(log_id=log.id)


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
