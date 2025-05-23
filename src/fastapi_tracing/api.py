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
import asyncio
import logging
import os
import random

from fastapi import Request, Response
from opentelemetry import trace

from .app import get_or_create_app
from .util import hash_multiple, require_auth

app = get_or_create_app()

_logger = logging.getLogger('api')


@app.get("/")
async def read_root(request: Request, auth: require_auth):
    """Responds with a friendly greeting

    Checks the 'NAME' environment variable, or just says hello to the 'World'.
    """
    return {"Hello": os.environ.get('NAME', 'World')}


@app.get("/ping")
async def ping_pong(auth: require_auth):
    """A simple health check, really. If you send 'ping', it says 'pong'."""
    return {"message": "pong"}


@app.get("/session")
async def get_session_info(request: Request, auth: require_auth):
    """Dumps a bunch of info about your current request.

    You know, headers, client details, that sort of thing.
    """
    return {
        "headers": dict(request.headers),
        "client_host": request.client.host if request.client else "unknown",
        "client_port": request.client.port if request.client else "unknown",
        "method": request.method,
        "url": str(request.url),
        "query_params": dict(request.query_params),
    }


@app.get("/slowish")
async def stable(auth: require_auth):
    """Takes a little nap, then tells you how long it snoozed.

    Sleeps for a random duration between 0 and 1 second.
    """
    duration = random.uniform(0, 1)
    await asyncio.sleep(duration)
    return {"message": f"i wasted exactly {duration:.4f} seconds"}


@app.get("/slow/and/unstable")
async def not_so_stable(response: Response, auth: require_auth):
    """This one's a bit of a gamble. Sleeps, then might throw an error.

    It'll tell you how long it took, whether it succeeded or failed.
    50/50 chance of a simulated error.
    """
    duration = random.uniform(0, 1)
    tracer = trace.get_tracer(__name__)
    with tracer.start_span('simulated work') as s:
        await asyncio.sleep(duration)
        if random.choice((True, False)):
            exc = RuntimeError('Simulated Exception')
            _logger.exception("This is a simulated error", exc_info=exc)
            response.status_code = 500
            return {'message': f'error in {duration:.4f} seconds: {exc}'}
        else:
            return {'message': f'success in {duration:.4f} seconds'}


@app.post("/hash")
async def expensive(request: Request, response: Response, auth: require_auth):
    """Does some pointless, heavy lifting by hashing your JSON request body.

    Also simulates some database and external calls for good measure.
    Expects a JSON body, or it'll complain.
    """
    if not await request.json():
        response.status_code = 400
        return {"message": "no json body"}

    tracer = trace.get_tracer(__name__)

    with tracer.start_span("pointless hashing operation"):
        body = await request.body()
        hash_val = hash_multiple(body.decode(), rounds=random.randint(100000, 1000000))

    with tracer.start_as_current_span("simulated work"):
        with tracer.start_span("db query") as s:
            _logger.info('Simulated DB query')
            duration = random.uniform(0, .1)
            await asyncio.sleep(duration)
            s.set_attribute("duration", duration)

        with tracer.start_span("simulated external call") as s:
            duration = random.uniform(0, .5)
            await asyncio.sleep(duration)
            if random.choice((True, False)):
                _logger.warning('Simulated external call failed')
            else:
                _logger.info('Simulated external call success')
            s.set_attribute("duration", duration)

    return {"message": "success", "hash": hash_val}
