import os

import django
from django.test import TestCase
from django.test.utils import setup_test_environment, teardown_test_environment

from pytest_django.compat import setup_databases, teardown_databases


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()


# Run with -D RESETDB=1 to rebuild the SQL database
def before_all(context):
    setup_test_environment()
    context.db_cfg = setup_databases(
        verbosity=False,
        interactive=False,
        keepdb=not context.config.userdata.getbool('RESETDB')
    )


def before_scenario(context, scenario):
    context.test_case = TestCase(methodName='__init__')
    context.test_case._pre_setup()


# Run with -D DEBUGGER=1 to enter ipdb upon exceptions
def after_step(context, step):
    if context.config.userdata.getbool('DEBUGGER') and step.status == 'failed':
        # -- ENTER DEBUGGER: Zoom in on failure location.
        import ipdb
        ipdb.post_mortem(step.exc_traceback)


def after_scenario(context, scenario):
    context.test_case._post_teardown()


def after_all(context):
    if context.config.userdata.getbool('RESETDB'):
        teardown_databases(context.db_cfg, verbosity=False)
    teardown_test_environment()
