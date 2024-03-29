import os

import django
from django.test import TestCase
from django.test.utils import (
    setup_test_environment,
    teardown_test_environment,
    setup_databases,
    teardown_databases,
)


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


def after_scenario(context, scenario):
    context.test_case._post_teardown()


def after_all(context):
    if context.config.userdata.getbool('RESETDB'):
        teardown_databases(context.db_cfg, verbosity=False)
    teardown_test_environment()
