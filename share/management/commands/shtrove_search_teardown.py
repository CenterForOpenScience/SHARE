from django.core.management.base import BaseCommand
from share.search import index_strategy


class Command(BaseCommand):
    help = "Drop Elasticsearch indices"

    def add_arguments(self, parser):
        parser.add_argument("strategy_names", nargs="+", help="List of strategy names to drop")

    def handle(self, *args, **options):
        for strategy_name in options["strategy_names"]:
            strategy = index_strategy.parse_strategy_name(strategy_name)
            strategy.pls_teardown()
