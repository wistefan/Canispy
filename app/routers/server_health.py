# Standard python library
import json
import logging

# The Fastapi web server
from fastapi import status, HTTPException, Body, Request, Depends
from fastapi import APIRouter

# For the data models
from typing import Dict, Optional, cast
from pydantic import BaseModel, BaseSettings

# The settings for the system
from settings import settings

from blockchain import canismajor


# Create logger
logging.basicConfig(
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.WARNING)
log = logging.getLogger(__name__)


router = APIRouter(
    tags=["Server Healh Status"]
)


#####################################################
# HEALTH CHECKING
#####################################################
@router.get("/api/ping")
def ping(request: Request):
    """A simple ping to check for server health
    """

    return {"payload": "Hello, v1.0.1"}

@router.get("/api/pinge2e")
def end_to_end_ping(request: Request):
    """End-to-end ping up to the Smart Contract to check that everything is working.
    """

    try:
        canismajor.checktimestamp()
    except Exception as e:
        detail = str(e)
        log.error(detail)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    # All went OK
    return {"payload": "Hello, v1.0.1"}
