from django.core.management.base import BaseCommand
from share.search import index_strategy
from share.search.exceptions import IndexStrategyError


class Command(BaseCommand):
    help = "Create Elasticsearch indices and apply mappings"

    def add_arguments(self, parser):
        parser.add_argument("index_or_strategy_name", nargs="?", help="Name of index or strategy")
        parser.add_argument("--initial", action="store_true", help="Set up all indices")

    def handle(self, *args, **options):
        if options["initial"]:
            for strategy in index_strategy.each_strategy():
                strategy.pls_setup()
        else:
            index_or_strategy_name = options["index_or_strategy_name"]
            if not index_or_strategy_name:
                self.stderr.write("Error: Missing index or strategy name")
                return
            try:
                strategy = index_strategy.get_strategy(index_or_strategy_name)
                strategy.pls_setup()
            except IndexStrategyError:
                raise IndexStrategyError(f'Unrecognized index or strategy name "{index_or_strategy_name}"')
