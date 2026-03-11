"""pwdx-ctl — PWD extraction, CRM lookup, and record creation."""
import click

@click.group()
@click.version_option('0.1.0')
def cli():
    """pwdx-ctl — ETA-9141 PWD extractor and CRM pipeline."""
    pass

from .commands.extract import extract
from .commands.lookup import lookup
from .commands.create import create

cli.add_command(extract)
cli.add_command(lookup)
cli.add_command(create)

if __name__ == '__main__':
    cli()
