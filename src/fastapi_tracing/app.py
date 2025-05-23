# Copyright 2025 Paul Durivage <durivage+github@google.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging

from fastapi import FastAPI

from . import __app_name__
from .ops import setup_otel, setup_structured_logging

_logger = logging.getLogger('app')


def _setup_app(app: FastAPI):
    """Wires up all the important bits for the FastAPI app.

    This means registering API routes and kicking off OpenTelemetry and logging.
    It also figures out which spans should be turned into metrics.
    """
    # Register routes.
    # We are intentionally not using this import. Importing runs the path decorators.
    from . import api  # noqa

    # Scrub all the registered methods to get them all automatically.
    # We really only want to capture the root traces for each path, so the easiest way is to
    # look at the routes registered with FastAPI.
    # If we wanted to limit this to an explict list of endpoints, we'd consider alternatives like
    # constructing it manually.
    spans_to_emit_as_metrics = set()
    for route in app.routes:
        for method in route.methods:
            spans_to_emit_as_metrics.add(f"{method} {route.path}")

    # Setup OpenTelemetry and logging
    setup_otel(app, spans_to_emit_as_metrics)
    setup_structured_logging(app_name=__app_name__)


def _create_app():
    """This closure insures we construct only a single instance of the app.  We also prevent a
    rat's nest of circular imports by exposing only a single app factory function
    """

    app_instance = None

    def inner():
        nonlocal app_instance
        if not app_instance:
            app_instance = FastAPI()
            _setup_app(app_instance)
        return app_instance

    return inner


get_or_create_app = _create_app()
