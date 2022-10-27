# Standard python library
import json
import logging

# The Fastapi web server
from fastapi import status, HTTPException, Body, Request, Depends, Header
from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

# For the data models
from typing import Dict, Optional, cast
from pydantic import BaseModel, BaseSettings

# The settings for the system
from settings import settings

from blockchain import canismajor

from utils.que import FIFOFile

# Create a persistent FIFO queue, using the default file name
f = FIFOFile(truncate=True)

# Create logger
logging.basicConfig(
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.WARNING)
log = logging.getLogger(__name__)

# Create the timestamping table, only if it does not exists
canismajor.create_db()

router = APIRouter()

def error_object(error_type: str, error_title: str = "", error_detail: str = "") -> dict:
    return {
            "type": error_type,
            "title": error_title,
            "detail": error_detail
    }

def check_request_requirements():
    pass

######################################################
# FIWARE Canis Major APIs
######################################################

link_object = 'Link: <https://json-ld.org/contexts/person.jsonld>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json'


@router.post("/ngsi-ld/v1/entities",
    response_class=ORJSONResponse,
    status_code=201,
    tags=["NGSI-LD Entity List"])
def entity_creation(
    Link: Optional[str] = Header(None),
    msg: dict = Body(
        ...,
        example={
            "@context": [
                "https://smartdatamodels.org/context.jsonld",
                "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
            ],
            "id": "urn:ngsi-ld:ParkingSpot:santander:daoiz_velarde_1_5:3",
            "type": "ParkingSpot",
            "status": {
                "type": "Property",
                "value": "free",
                "observedAt": "2018-09-21T12:00:00Z",
                "parkingPermit": {
                    "type": "Property",
                    "value": "yes"
                }
            },
            "category": {
                "type": "Property",
                "value": [
                    "onStreet"
                ]
            },
            "refParkingSite": {
                "type": "Relationship",
                "object": "urn:ngsi-ld:ParkingSite:santander:daoiz_velarde_1_5"
            },
            "name": {
                "type": "Property",
                "value": "A-13"
            },
            "location": {
                "type": "GeoProperty",
                "value": {
                    "type": "Point",
                    "coordinates": [
                        -3.80356167695194,
                        43.46296641666926
                    ]
                }
            }
        }
    )
):
    """Register the hash of the new entity created on Context Broker.
    """

    if Link is None:
        pass

    # The received JSON object must have "@context", "id" and "type" fields
    if ("id" not in msg) or ("type" not in msg):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing @context, id or type fields"
        )

    # Register and timestamp the received message in the blockchain
    receipt = canismajor.timestamp(msg["id"], msg)

    return receipt

@router.get("/ngsi-ld/v1/entities",
    response_class=ORJSONResponse,
    tags=["NGSI-LD Entity List"])
def query_entities():
    """List all entities.
    """
    items = canismajor.list_all()
    return items


@router.get("/ngsi-ld/v1/entities/{entityId}",
    response_class=ORJSONResponse,
    tags=["NGSI-LD Entity by ID"])
def entity_retrieval_by_id(entityId: str):
    """List one entity.
    """
    item = canismajor.list_one_item(entityId)
    return item

@router.delete("/ngsi-ld/v1/entities/{entityId}",
    response_class=ORJSONResponse,
    tags=["NGSI-LD Entity by ID"])
def entity_delete_by_id(entityId: str):
    """List one entity.
    """
    return {"message": "Not yet implemented"}

@router.post("/ngsi-ld/v1/entities/{entityId}/attrs/",
    response_class=ORJSONResponse,
    tags=["NGSI-LD Entity Attribute List"])
def append_entity_attributes(entityId: str):
    """List one entity.
    """
    item = canismajor.list_one_item(entityId)
    return item

@router.patch("/ngsi-ld/v1/entities/{entityId}/attrs/",
    response_class=ORJSONResponse,
    tags=["NGSI-LD Entity Attribute List"])
def update_entity_attributes(entityId: str):
    """List one entity.
    """
    item = canismajor.list_one_item(entityId)
    return item


@router.get("/ngsi-ld/v1/entities/txreceipt/{tx_hash}",
    response_class=ORJSONResponse,
    tags=["NGSI-LD Entity Blockchain Proof"])
def entity_proof_from_dlt(tx_hash: str):
    """Get the transaction receipt from the blockchain.
    """
    receipt = canismajor.get_receipt(tx_hash)

    return receipt

@router.post("/v2/entities",
    response_class=ORJSONResponse,
    tags=["NGSI V2 Entity Creation"])
def entity_creation_v2(
    msg: dict = Body(
        ...,
        example={
            "id": "santander:daoiz_velarde_1_5:3",
            "type": "ParkingSpot",
            "name": "A-13",
            "location": {
                "type": "Point",
                "coordinates": [-3.80356167695194, 43.46296641666926]
            },
            "status": "free",
            "category": ["onStreet"],
            "refParkingSite": "santander:daoiz_velarde_1_5"
        }
    )
):
    """Register the hash of the new entity created on Context Broker.
    """

    # The received JSON object must have an "id" and a "type" fields
    if ("id" not in msg) or ("type" not in msg):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing id or type fields"
        )

    # Register and timestamp the received message in the blockchain
    receipt = canismajor.timestamp(msg["id"], msg)

    return receipt

