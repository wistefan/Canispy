# Standard python library
import json
import logging

# The Fastapi web server
from fastapi import status, HTTPException, Body, Request, Depends
from fastapi import APIRouter

# For the data models
from typing import Dict, Optional, cast
from pydantic import BaseModel, BaseSettings

# A very fast cache with expiration
from cachetools import TTLCache

# The settings for the system
from settings import settings

# Create logger
logging.basicConfig(
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.WARNING)
log = logging.getLogger(__name__)


router = APIRouter(
    tags=["Secure Messaging Server"]
)


#####################################################
# MESSAGING SERVER
#####################################################

# Create the cache for messaging credentials
c = TTLCache(settings.TTLCACHE_NUM_ELEMENTS, settings.TTLCACHE_EXPIRATION)


# The message that is sent or received, with an opaque payload (but must be string)
class Message(BaseModel):
    payload: str


@router.post("/api/write/{sessionKey}")
def write_item(sessionKey: str, msg: Message):
    """Write a payload to the cache associated to a sessionKey.
    This API is used to send a Credential to a receiver. It is used by:
    1. The Issuer when sending a credential to the Passenger
    2. The Passenger when sending a credential to the Verifier
    """

    # Check if we have received some data in the POST
    if len(msg.payload) == 0:
        log.error("No data received")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No data received")

    # Store in the cache and return the session key
    c[sessionKey] = msg.payload
    return {"sessionKey": sessionKey}


@router.get("/api/read/{sessionKey}", response_model=Message)
def read_item(sessionKey):
    """Read the payload from the cache specifying the unique sessionKey.
    This API is used to receive a Credential from a sender. It is used by:
    1. The Issuer when receiving a credential from the Issuer
    2. The Verifier when receiving a credential from the Passenger
    """

    # Try to get the element from the cache, erasing it if it exists
    payload = c.pop(sessionKey, "")
    return {"payload": payload}

