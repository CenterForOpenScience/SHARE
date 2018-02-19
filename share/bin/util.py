import os
import sys

from docopt import docopt

from django.conf import settings


class Command:

    @property
    def subcommand_list(self):
        indent = (4 + max([len(k) for k in self.subcommands], default=0))
        return '\n'.join(
            self.subcommands[k].teaser(indent)
            for k in sorted(self.subcommands)
        )

    def __init__(self, func, description, parsed=True):
        self.bin = os.path.basename(sys.argv[0])
        self.description = description
        self.func = func
        self.parsed = parsed
        self.subcommands = {}
        self.docstring = '\n'.join(x[4:] for x in (func.__doc__ or '').split('\n'))
        self.name = func.__name__

    def teaser(self, indent):
        return '    {{0.name:{}}}{{0.description}}'.format(indent).format(self)

    def subcommand(self, description, parsed=True):
        def _inner(func):
            return self.register(func, description, parsed)
        return _inner

    def register(self, func, description, parsed=True):
        cmd = type(self)(func, description, parsed)
        if cmd.name in self.subcommands:
            raise ValueError('{} already defined'.format(cmd.name))
        self.subcommands[cmd.name] = cmd
        return cmd

    def __call__(self, argv):
        if not self.parsed:
            args = {}
        else:
            try:
                options_first = self is execute_cmd or (argv[argv.index(self.name) + 1] in self.subcommands)
            except IndexError:
                options_first = False

            args = docopt(
                self.docstring.format(self.bin, self),
                argv=argv,
                version=settings.VERSION,
                options_first=options_first,
            )

        if args.get('<command>') and self.subcommands:
            if not args['<command>'] in self.subcommands:
                print('Invalid command "{<command>}"'.format(**args))
                return sys.exit(1)
            return self.subcommands[args['<command>']](argv)
        return self.func(args, argv)


def _execute_cmd(args, argv):
    """
    Usage:
        {0} <command> [<args>...]
        {0} (--version | --help)

    Options:
        -h, --help     Show this screen.
        -v, --version  Show version.

    Commands:
    {1.subcommand_list}

    See '{0} <command> --help' for more information on a specific command."""
    return 0


execute_cmd = Command(_execute_cmd, '')
command = execute_cmd.subcommand
