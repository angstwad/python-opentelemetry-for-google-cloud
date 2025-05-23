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
import hashlib
import logging
import random
from typing import Annotated

from fastapi import Request, HTTPException, Depends
from opentelemetry import trace

_logger = logging.getLogger("util")


def hash_multiple(input_str: str, rounds: int = 1000) -> str:
    """Repeatedly hashes a string using SHA512.

    Args:
        input_str: The string to be hashed.
        rounds: The number of hashing iterations. Defaults to 1000.

    Returns:
        The resulting hexadecimal string after all hashing rounds.
    """
    _logger.info(f"Hashing {rounds} rounds")
    current_hash = hashlib.sha512(input_str.encode()).hexdigest()
    for _ in range(rounds):
        current_hash = hashlib.sha512(current_hash.encode()).hexdigest()
    return current_hash


async def authenticate(request: Request):
    """Simulates an authentication check based on the Authorization header.

    This is NOT suitable in any production environment.

    This function checks for the presence of an 'Authorization' header.
    If the header is missing, it raises an HTTPException. It also
    simulates fetching user session data.

    Args:
        request: The incoming FastAPI request.

    Raises:
        HTTPException: With a 401 status code if the 'Authorization' header is absent.

    Returns:
        True if the 'Authorization' header is present.
    """
    _logger.info("Simulating authentication")
    auth_header = request.headers.get('Authorization')
    _logger.info(f'{"" if auth_header else "No "}Authorization header received')
    if not auth_header:
        raise HTTPException(status_code=401, detail="Unauthorized")
    await get_user_session(request)
    return True  # Reaching here means auth_header was present


async def get_user_session(request: Request):
    """Simulates fetching user session data with a random delay.

    This function is primarily for demonstration, introducing an artificial
    delay within an OpenTelemetry span.

    Args:
        request: The incoming FastAPI request (currently unused within the function).
    """
    _logger.info("Simulating getting user session")
    tracer = trace.get_tracer(__name__)
    with tracer.start_span("get_user_session"):
        await asyncio.sleep(random.uniform(0, .5))


# Defines a dependency that enforces authentication for an endpoint.
require_auth = Annotated[bool, Depends(authenticate)]
