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

# Create logger
logging.basicConfig(
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.WARNING)
log = logging.getLogger(__name__)

# Create a cache for 100 DID Documents for 3 hours
doc_cache = TTLCache(100, 3*60*60)


router = APIRouter(
    tags=["Universal Resolver: DID resolution"]
)

################################################################################
# PUBLIC APIS (DO NOT NEED AUTHENTICATION)
# Intended for public consumption because they are a "public good"
# They have to be protected from DoS attacks, for example rate-limiting them
# behind a reverse proxy like Nginx
################################################################################

######################################################
# UNIVERSAL RESOLVER: DID RESOLUTION
######################################################

# The reply message
class DIDDocument_reply(BaseModel):
    payload: Dict

    class Config:
        schema_extra = {
            "example": {
                "@context": [
                    "https://www.w3.org/ns/did/v1",
                    "https://w3id.org/security/v1"
                ],
                "id": "did:elsi:VATES-B60645900",
                "publicKey": [
                    {
                        "id": "did:elsi:VATES-B60645900#key-verification",
                        "type": "JwsVerificationKey2020",
                        "controller": "did:elsi:VATES-B60645900",
                        "publicKeyJwk": {
                            "kid": "key-verification",
                            "kty": "EC",
                            "crv": "secp256k1",
                            "x": "QoHDiX_hLAm7M__qUyCXRod6jzx0tCxS-_RoIjP1xzg",
                            "y": "Tqp4fFlMb6YcW-3b86kKjcpx8TyIg4Mkb5Q3nB5bgq4"
                        }
                    }
                ],
                "service": [
                    {
                        "id": "did:elsi:VATES-B60645900#info",
                        "type": "EntityCommercialInfo",
                        "serviceEndpoint": "www.in2.es",
                        "name": "IN2"
                    }
                ],
                "alaExtension": {
                    "redT": {
                        "domain": "in2.ala",
                        "ethereumAddress": "0x202e88FA672F65810e5Ed0EF84fFe919063d4E60"
                    }
                },
                "created": "2020-12-23T13:35:23Z",
                "updated": "2020-12-23T13:35:23Z"
            }
        }

# Resolves a DID and returns the DID Document (JSON format), if it exists
# We support four DID methods: ebsi, elsi, ala, peer.
# TODO: support LACChain DIDs


@router.get("/api/did/v1/identifiers/{DID}", response_model=DIDDocument_reply)
def resolve_DID(DID: str):
    """Resolves a DID and returns the DID Document (JSON format), if it exists.  
    We support four DID methods: **ebsi**, **elsi**, **ala**, **peer**.

    Only **PEER** and **ELSI** (*https://github.com/hesusruiz/SafeIsland#62-elsi-a-novel-did-method-for-legal-entities*) are directly
    implemented by this API.
    The others are delegated to be resolved by their respective implementations.

    For example, for **EBSI** we call the corresponding Universal Resolver API, currently in testing and available at
    *https://api.ebsi.xyz/did/v1/identifiers/{did}*
    """

    # Parse the DID and check if it is one of the supported types
    try:
        did_struct = didutils.parseDid(DID)
    except didutils.DIDParseError as e:
        detail = str(e)
        log.error(detail)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    # DIDs and associated DID Documents do not change a lot after creation
    # Caching the DID Documents for several hours is an acceptable compromise
    # and can increase performance substantially (default: 3 hours)
    # Check if the DID is already in the cache
    didDoc = cast(dict, doc_cache.get(DID))
    if didDoc is not None:
        return {"payload": didDoc}

    did_method = did_struct["method"]

    # Process ELSI DID method
    if did_method == "elsi":

        # Try to resolve from the blockchain node
        try:
            _DID, name, didDoc, active = tf.resolver.resolveDID(DID)
        except Exception as e:
            detail = str(e)
            log.error(detail)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

        if didDoc is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="DID not found")

        # Store the DID and associated DIDDocument in the cache
        doc_cache[DID] = didDoc

        return {"payload": didDoc}

    # Process EBSI DID method
    elif did_method == "ebsi":

        # When EBSI reaches production, we will resolve the DID using the API
        # which now is at:
        # Note that it is a Universal Resolver API like this one
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not implemented")

    # Process AlastriaID DID method
    elif did_method == "ala":

        # When AlastriaID (standard) reaches production, we will resolve the DID
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not implemented")

    # Process Peer DID method
    elif did_method == "peer":

        # TODO: implement the Peer DID
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not implemented")

    # Should not reach here
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="DID parsing failed")


######################################################
# Lists the Trusted Issuers in the system
######################################################

@router.get("/api/trusted-issuers-registry/v1/issuers")
def list_trusted_issuers():
    """Returns the list of all trusted issuers registered in the blockchain for the SafeIsland ecosystem.
    """

    # Query the blockchain and manage exceptions
    try:
        trusted_issuers = tf.dump_trusted_identities()
    except Exception as e:
        detail = str(e)
        log.error(detail)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return {"payload": trusted_issuers}

