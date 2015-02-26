import elasticsearch
import click
import re
from .utils import *
from .. import __version__

import logging
logger = logging.getLogger(__name__)

try:
    from logging import NullHandler
except ImportError:
    from logging import Handler

    class NullHandler(Handler):
        def emit(self, record):
            pass

DEFAULT_ARGS = {
    'host': 'localhost',
    'url_prefix': '',
    'port': 9200,
    'auth': None,
    'ssl': False,
    'timeout': 30,
    'dry_run': False,
    'debug': False,
    'log_level': 'INFO',
    'logformat': 'Default',
}

@click.group()
@click.option('--host', help='Elasticsearch host.', default=DEFAULT_ARGS['host'])
@click.option('--url_prefix', help='Elasticsearch http url prefix.', default=DEFAULT_ARGS['url_prefix'])
@click.option('--port', help='Elasticsearch port.', default=DEFAULT_ARGS['port'], type=int)
@click.option('--ssl', help='Connect to Elasticsearch through SSL.', is_flag=True, default=DEFAULT_ARGS['ssl'])
@click.option('--auth', help='Use Basic Authentication ex: user:pass', default=DEFAULT_ARGS['auth'])
@click.option('--timeout', help='Connection timeout in seconds.', default=DEFAULT_ARGS['timeout'], type=int)
@click.option('--master-only', is_flag=True, help='Only operate on elected master node.')
@click.option('--dry-run', is_flag=True, help='Do not perform any changes.', default=DEFAULT_ARGS['dry_run'])
@click.option('--debug', is_flag=True, help='Debug mode', default=DEFAULT_ARGS['debug'])
@click.option('--loglevel', help='Log level', default=DEFAULT_ARGS['log_level'])
@click.option('--logfile', help='log file')
@click.option('--logformat', help='Log output format [default|logstash].', default=DEFAULT_ARGS['logformat'])
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, host, url_prefix, port, ssl, auth, timeout, master_only, dry_run, debug, loglevel, logfile, logformat):
    """Curator for Elasticsearch indices. See http://github.com/elasticsearch/curator/wiki
    """
    # Check for --help flag
    args = " ".join(sys.argv)
    pattern = re.compile(r'^.*\-\-help.*$')
    wants_help = pattern.match(args)

    # If no --help flag, then begin in earnest...
    if not wants_help:
        # Setup logging
        if debug:
            numeric_log_level = logging.DEBUG
            format_string = '%(asctime)s %(levelname)-9s %(name)22s %(funcName)22s:%(lineno)-4d %(message)s'
        else:
            numeric_log_level = getattr(logging, loglevel.upper(), None)
            format_string = '%(asctime)s %(levelname)-9s %(message)s'
            if not isinstance(numeric_log_level, int):
                raise ValueError('Invalid log level: {0}'.format(loglevel))

        handler = logging.StreamHandler(
            open(logfile, 'a') if logfile else sys.stderr)
        if logformat == 'logstash':
            handler.setFormatter(LogstashFormatter())
        else:
            handler.setFormatter(logging.Formatter(format_string))
        logging.root.addHandler(handler)
        logging.root.setLevel(numeric_log_level)

        # Filter out logging from Elasticsearch and associated modules by default
        if not debug:
            for handler in logging.root.handlers:
                handler.addFilter(Whitelist('root', '__main__', 'curator', 'curator.curator', 'curator.api', 'curator.cli'))

        # Setting up NullHandler to handle nested elasticsearch.trace Logger instance in elasticsearch python client
        logging.getLogger('elasticsearch.trace').addHandler(NullHandler())

        logging.info("Job starting...")

        if dry_run:
            logging.info("DRY RUN MODE.  No changes will be made.")

        ctx.obj["client"] = get_client(ctx)

        # Get a master-list of indices
        indices = get_indices(ctx.obj["client"])
        if indices:
            ctx.obj["indices"] = indices
        else:
            click.echo(click.style('ERROR. Unable to get indices from Elasticsearch.', fg='red', bold=True))
            sys.exit(1)
