"""grab-bag of handy utilities that will be available in the django shell

that is, the shell you get from `python manage.py shell_plus`
"""

from share import tasks
from share.search import IndexMessenger, IndexStrategy
from share.util import IDObfuscator


__all__ = (
    'tasks',
    'IndexMessenger',
    'IndexStrategy',
    'IDObfuscator',
)
