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

# From this project packages
from blockchain import trustframework as tf
from blockchain import wallet, didutils, safeisland, pubcred, redt



# Create logger
logging.basicConfig(
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.WARNING)
log = logging.getLogger(__name__)


router = APIRouter(
    tags=["Protected APIs for Issuer"]
)

################################################################################
# PROTECTED APIS (REQUIRE AUTHENTICATION)
# Intended for Issuer
# Intended for Issuer
# Intended for Issuer
# Intended for Issuer
################################################################################

#####################################################
# APIS FOR USAGE BY THE ISSUER MOBILE APP
#####################################################

# Get a list of credentials from the database in the server in JSON
@router.get("/api/verifiable-credential/v1/credentials")
def credential_list():
    """Get a list of credentials from the database in the server in JSON
    """
    rows = safeisland.list_certificates()
    certs = []
    for row in rows:
        #        certs.append(row["cert"])
        certs.append({"uuid": row["uuid"], "cert": row["cert"]})

    return {"payload": certs}


# Gets a credential (JSON) from issuer by specifying its uniqueID
@router.get("/api/verifiable-credential/v1/{uniqueID}")
def credential_get(uniqueID: str):
    """Gets a credential (JSON) from issuer by specifying its uniqueID
    """

    cert = safeisland.certificate(uniqueID)
    return {"payload": cert}


# Get a list of public credentials from the database in the server in JSON
@router.get("/api/verifiable-credential/v1/public/credentials")
def public_credential_list():
    """Get a list of public credentials from the database in the server in JSON
    """
    rows = pubcred.list_certificates()
    certs = []
    for row in rows:
        #        certs.append(row["cert"])
        certs.append({"uuid": row["uuid"], "cert": row["cert"]})

    return {"payload": certs}

# Gets a credential (JSON) from issuer by specifying its uniqueID


@router.get("/api/verifiable-credential/v1/public/{uniqueID}")
def public_credential_get(uniqueID: str):
    """Gets a public credential (JSON) from issuer by specifying its uniqueID
    """

    cert = pubcred.certificate(uniqueID)
#    return {"payload": cert}
    return cert


#####################################################
# CREATE A PRIVATE KEY
#####################################################

# The reply message
class CreatePrivateKey_reply(BaseModel):
    kty: str
    crv: str
    d: str
    x: str
    y: str


@router.post("/api/wallet/v1/privatekey", response_model=CreatePrivateKey_reply)
def create_privatekey():
    """ Create a private key that can be used to create an identity in the blockchain
    """

    # Generate the private key
    key_jwk = wallet.create_JWK()
    response_jwk = key_jwk.export(private_key=True, as_dict=True)

    return response_jwk


@router.get("/api/wallet/v1/privatekey/{account}/{password}", response_model=CreatePrivateKey_reply)
def get_privatekey(account: str, password: str):
    """Get an existing private key in the wallet.
    Must specify an existing account name and its password
    """

    key_jwk = wallet.key_JWK(account, password)
    response_jwk = key_jwk.export(private_key=True, as_dict=True)

    return response_jwk


#######################################################
# CREATE AN IDENTITY AS A SUBNODE FROM THE CALLER NODE
#######################################################

# The input message

class PublickeyJWK(BaseModel):
    kty: str
    crv: str
    x: str
    y: str


class PrivatekeyJWK(PublickeyJWK):
    d: str


class CreateIdentity_request(BaseModel):
    # ELSI DID of the new identity, example: "did:elsi:VATES-B60645900"
    DID: str
    # Blockchain domain name to assign, example: "in2.ala"
    domain_name: str
    website: str                        # Website of the entity, example: "www.in2.es"
    # Commercial name, example: "IN2 Innovating 2gether"
    commercial_name: str
    new_privatekey: PrivatekeyJWK         # The private key of the new entity
    # The Private Key of caller (in this case the owner of "ala")
    parent_privatekey: PrivatekeyJWK

    class Config:
        schema_extra = {
            "example": {
                "DID": "did:elsi:VATES-B60645900",
                "domain_name": "in2.ala",
                "website": "www.in2.es",
                "commercial_name": "IN2 Innovating 2gether",
                "new_privatekey": {
                    "kty": "EC",
                    "crv": "secp256k1",
                    "d": "Dqv3jmu8VNMKXWrHkppr5473sLMzWBczRhzdSdpxDfI",
                    "x": "FTiW0a4r7S2SwjL7AlFlN1yJNWF--4_x3XTTxkFbJ9o",
                    "y": "MmpxbQCOZ0L9U6rLLkD_U8LRGwYEHcoN-DPnEdlpt6A"
                },
                "parent_privatekey": {
                    "kty": "EC",
                    "crv": "secp256k1",
                    "d": "Dqv3jmu8VNMKXWrHkppr5473sLMzWBczRhzdSdpxDfI",
                    "x": "NKW_0Fs4iumEegzKoOH0Trwtje1sXsG9Z1949sA8Omo",
                    "y": "g4B3EI0qIdlcXTn-2RpUxgVX-sxNFdqCQDD0aHztVkk"
                }
            }
        }


# The reply message
class CreateIdentity_reply(BaseModel):
    didDoc: Dict


@router.post("/api/did/v1/identifiers", response_model=CreateIdentity_reply)
def create_identity(msg: CreateIdentity_request):
    """Create an Identity anchored in the blockchain
    """

    # Check if we have received some data in the POST
    if len(msg.DID) == 0:
        log.error("No data received")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No data received")

    # Create the identity using the library
    try:
        error, didDoc = tf.create_identity_subnode(
            msg.DID, msg.domain_name, msg.website, msg.commercial_name, msg.new_privatekey, msg.parent_privatekey)
    except Exception as e:
        detail = str(e)
        log.error(detail)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if error is not None:
        log.error(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {"didDoc": didDoc.to_dict()}

# The input message, assuming the server has a wallet


class CreateIdentity_request_wallet(BaseModel):
    # ELSI DID of the new identity, example: "did:elsi:VATES-B60645900"
    DID: str
    domain_name: str            # Blockchain domain name to assign, example: "in2.ala"
    website: str                # Website of the entity, example: "www.in2.es"
    commercial_name: str        # Commercial name, example: "IN2 Innovating 2gether"
    parent_node_account: str    # Account that owns the parent node, example: "Alastria"
    password: str               # Password to encrypt private key, example: "ThePassword"

    class Config:
        schema_extra = {
            "example": {
                "DID": "did:elsi:VATES-B60645900",
                "domain_name": "in2.ala",
                "website": "www.in2.es",
                "commercial_name": "IN2 Innovating 2gether",
                "parent_node_account": "Alastria",
                "password": "ThePassword"
            }
        }


@router.post("/api/did/v1/wallet/identifiers", response_model=CreateIdentity_reply)
def create_identity_with_wallet(msg: CreateIdentity_request_wallet):
    """Create an identity anchored in the blockchain, using an existing account in the server
    """

    # Check if we have received some data in the POST
    if len(msg.DID) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No data received")

    # Create the identity using the library
    error, didDoc = tf.create_identity(
        msg.DID, msg.domain_name, msg.website, msg.commercial_name, msg.parent_node_account, msg.password)
    if error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return didDoc.to_dict()


