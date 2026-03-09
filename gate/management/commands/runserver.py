"""
Custom runserver that suppresses noisy tracebacks when the client aborts
the connection (e.g. user navigates away, iframe unload, service worker).
"""
import logging

from django.contrib.staticfiles.management.commands.runserver import (
    Command as RunserverCommand,
)
from django.core.servers import basehttp

logger = logging.getLogger('django.server')

# Connection errors that mean "client disconnected" - not a server bug
CONNECTION_ABORT_EXCEPTIONS = (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)


class QuietWSGIRequestHandler(basehttp.WSGIRequestHandler):
    """Request handler that logs client disconnects instead of full tracebacks."""

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except CONNECTION_ABORT_EXCEPTIONS:
            logger.info(
                "Client disconnected from %s",
                self.address_string(),
                extra={
                    'request': self.request,
                    'server_time': self.log_date_time_string(),
                },
            )


class Command(RunserverCommand):
    help = (
        "Starts a lightweight Web server for development, serves static files, "
        "and suppresses noisy tracebacks when clients disconnect."
    )

    def inner_run(self, *args, **options):
        # Use our handler so client aborts don't print full tracebacks
        basehttp.WSGIRequestHandler = QuietWSGIRequestHandler
        super().inner_run(*args, **options)
