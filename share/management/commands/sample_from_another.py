
from share.management.commands import BaseShareCommand


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        parser.add_argument('another_share_irl', default='https://share.osf.io/')
        parser.add_argument('sample_size', type=int, default=1123)

    def handle(self, *args, **options):
        # 
