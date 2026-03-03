"""CLI context and decorators."""

import click


class Context:
    def __init__(self):
        self.config = None
        self.client = None
        self.verbose = False
        self.output_format = None


pass_context = click.make_pass_decorator(Context, ensure=True)
