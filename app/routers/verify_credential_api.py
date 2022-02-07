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

# A very fast cache with expiration
from cachetools import TTLCache

# From this project packages
from blockchain import trustframework as tf
from blockchain import wallet, didutils, safeisland, pubcred, redt

# JWT support
from jwcrypto.common import JWException

# Create logger
logging.basicConfig(
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.WARNING)
log = logging.getLogger(__name__)

# Create a cache for 100 DID Documents for 3 hours
doc_cache = TTLCache(100, 3*60*60)

router = APIRouter(
    tags=["EBSI-style Verifiable Credentials"]
)

#####################################################
# Verify a Credential, checking its digital signature
# with the Identity of the Issuer in the Blockchain
#####################################################

# The message that is sent or received, with an opaque payload (but must be string)
class VerifyJWTMessage(BaseModel):
    payload: str    # The JWT in JWS Compact Serialization format as specified in IETF RFC 7519

    class Config:
        schema_extra = {
            "example": {
                "payload": "The JWT in JWS Compact Serialization format as specified in IETF RFC 7519"
            }
        }


@router.post("/api/verifiable-credential/v1/verifiable-credential-validations")
def credential_verify(msg: VerifyJWTMessage):
    """Verify a Credential in JWT format, checking its digital signature
    with the Identity of the Issuer in the Blockchain.
    """

    # Check if we have received some data in the POST
    jwt_cert = msg.payload
    if len(jwt_cert) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No data received")

    # Verify the certificate
    try:
        claims, didDoc = safeisland.verify_cert_token(jwt_cert)
    except JWException as e:
        detail = str(e)
        log.error(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    except Exception as e:
        detail = str(e)
        log.error(detail)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if claims is None:
        log.error("Verification of token failed")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Verification of token failed")

    # If we reached here, the JWT was verified and can return the claims in JSON format
    return {"payload": claims, "diddoc": didDoc.to_dict()}
