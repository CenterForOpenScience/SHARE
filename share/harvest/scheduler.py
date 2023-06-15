import pendulum

from django.db import models

from share.models import HarvestJob


class HarvestScheduler:
    """Utility class for creating HarvestJobs

    All date ranges are treated as [start, end)

    """

    def __init__(self, source_config, claim_jobs=False):
        self.source_config = source_config
        self.claim_jobs = claim_jobs

    def all(self, cutoff=None, allow_full_harvest=True, **kwargs):
        """
        Args:
            cutoff (date, optional): The upper bound to schedule harvests to. Default to today.
            allow_full_harvest (bool, optional): Allow a SourceConfig to generate a full harvest. Defaults to True.
                The SourceConfig.full_harvest must be marked True and have earliest_date set.
            **kwargs: Forwarded to .range

        Returns:
            A list of harvest jobs

        """
        if cutoff is None:
            cutoff = pendulum.now().date()

        # TODO take harvest/sourceconfig version into account here
        if hasattr(self.source_config, 'latest'):
            latest_date = self.source_config.latest
        else:
            latest_date = self.source_config.harvest_jobs.aggregate(models.Max('end_date'))['end_date__max']

        # If we can build full harvests and the earliest job that would be generated does NOT exist
        # Go ahead and reset the latest_date to the earliest_date
        if allow_full_harvest and self.source_config.earliest_date and self.source_config.full_harvest:
            if not self.source_config.harvest_jobs.filter(start_date=self.source_config.earliest_date).exists():
                latest_date = self.source_config.earliest_date

        # If nothing sets latest_date, default to the soonest possible harvest
        if not latest_date:
            latest_date = cutoff - self.source_config.harvest_interval

        return self.range(latest_date, cutoff, **kwargs)

    def today(self, **kwargs):
        """
        Functionally the same as calling .range(today, tomorrow)[0].
        You probably want to use .yesterday rather than .today.

        Args:
            **kwargs: Forwarded to .date

        Returns:
            A single Harvest job that *includes* today.

        """
        return self.date(pendulum.today().date(), **kwargs)

    def yesterday(self, **kwargs):
        """
        Functionally the same as calling .range(yesterday, today)[0].

        Args:
            **kwargs: Forwarded to .date

        Returns:
            A single Harvest job that *includes* yesterday.

        """
        return self.date(pendulum.yesterday().date(), **kwargs)

    def date(self, date, **kwargs):
        """
        Args:
            date (date):
            **kwargs: Forwarded to .range

        Returns:
            A single Harvest job that *includes* date.

        """
        return self.range(date, date.add(days=1), **kwargs)[0]

    def range(self, start, end, save=True):
        """

        Args:
            start (date):
            end (date):
            save (bool, optional): If True, attempt to save the created HarvestJobs. Defaults to True.

        Returns:
            A list of HarvestJobs within [start, end).

        """
        jobs = []

        job_kwargs = {
            'source_config': self.source_config,
        }
        if self.claim_jobs:
            job_kwargs['claimed'] = True

        start = pendulum.datetime(start.year, start.month, start.day)
        end = pendulum.datetime(end.year, end.month, end.day)

        sd, ed = start, start

        while ed + self.source_config.harvest_interval <= end:
            sd, ed = ed, ed + self.source_config.harvest_interval
            jobs.append(HarvestJob(start_date=sd, end_date=ed, **job_kwargs))

        if jobs and save:
            return HarvestJob.objects.bulk_get_or_create(jobs)

        return jobs
