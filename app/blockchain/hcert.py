import os
import time
import sqlite3
import json
import uuid as unique_id
from sqlite3.dbapi2 import Connection
from eth_utils.crypto import keccak
from hexbytes import HexBytes
from dataclasses import dataclass

import cwt
from cwt import cose_key

from pydantic import BaseModel
from typing import Optional, Tuple, Sequence

from devtools import debug

from web3.main import Web3

from blockchain import trustframework as tf
from blockchain import wallet

from jwcrypto import jwt, jwk, jws
from jwcrypto.common import base64url_decode, base64url_encode, json_decode, json_encode

from settings import settings

if settings.PRODUCTION:
    DATABASE_FILE = "hcert.sqlite"
else:
    DATABASE_FILE = "hcert.test.sqlite"

DATABASE_NAME = os.path.join(settings.DATABASE_DIR, DATABASE_FILE)

class HException(Exception):
    """Base class for exceptions in this module."""
    pass

table_schema = """
DROP TABLE IF EXISTS hcert;

CREATE TABLE hcert (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ctype TEXT NOT NULL,
  sformat TEXT NOT NULL,
  uuid TEXT UNIQUE NOT NULL,
  cert TEXT NOT NULL
);
"""

# ctype: certificate type. DGC (Digital Green Certificate), PUBCRED (Public Credential), ...
# sformat: storage format, ready for transmission via QR or any other mechanism. JWT, CWT, ...
# uuid: Unique Identifier. Can be in EU COVID format or any other, as long as it is unique
# cert: the actual certificate in serialized format as specified by sformat


def get_db() -> Connection:
    print(DATABASE_NAME)
    db = sqlite3.connect(DATABASE_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db


def erase_db() -> Connection:
    """Erase the HCERT table

    """

    # Connect the database (in case of SQLite just opens the file)
    db = get_db()

    # Erase and create the table from scratch
    print(f"\n==> Creating the database schema")
    db.executescript(table_schema)
    print(f"Database schema created")

    return db


def new_record(uuid: str, ctype: str, sformat: str, cert: str) -> str:

    db = get_db()

    db.execute(
        'REPLACE INTO pubcred (uuid, ctype, sformat, cert) VALUES (?, ?, ?, ?)',
        (uuid, ctype, sformat, cert)
    )
    # Commit database
    db.commit()

    # Return certificate id to caller
    return uuid


def record(uuid: str) -> str:

    db = get_db()

    cert = db.execute(
        'SELECT * FROM pubcred WHERE uuid = ?', (uuid,)
    ).fetchone()

    if cert is None:
        return None

    # Get the serialized format of the certificate
    cert = cert["cert"]

    return cert


def list_records():

    db = get_db()

    certs = db.execute('SELECT * FROM pubcred ORDER BY uuid').fetchall()

    return certs

################################################################################
# HCERT definitions
################################################################################


CWT_ISS = 1
CWT_IAT = 6
CWT_EXP = 4
CWT_HCERTL = -261
CWT_EU_DGC_V1 = 1

def new_unsigned_hcert_test(
    iss: str,   # Issuer DID
    iat: int,   # Issuance time
    exp: int,   # Expiration time

    fn: str,    # Family name
    fnt: str,   # Standardised family name
    gn: str,    # Given name
    gnt: str,   # Standardised given name
    dob: str,   # Date of birth

    tg: str,    # Disease agent targeted
    tt: str,    # Type of Test
    nm: str,    # NAA Test Name
    ma: str,    # RAT Test name and manufacturer
    sc: str,    # Date/Time of Sample Collection
    dr: str,    # Date/Time of Test Result
    tr: str,    # Test Result
    tc: str,    # Testing Centre
    co: str,    # Country of Test
    is: str,    # Certificate Issuer
    ci: str,    # Unique Certificate Identifier, UVCI
    ):
    """Create an HCERT claims object for a Verifiable Credential in CWT format.
    The returned object has just the plain claims object, and has to be
    signed later.
    """

    # Generate a random UUID, not related to anything in the credential
    # This is important for privacy reasons to avoid possibility of
    # correlation if the UUID is used for Revocation Lists in a blockchain
    if not ci:
        ci = unique_id.uuid4().hex

    # Current time and expiration
    if not iat:
        iat = int(time.time())
    
    if not exp:
        exp = iat + 10*24*60*60  # The token will expire in 10 days

    # Generate a template Verifiable Credential
    credential = {
        CWT_ISS: iss,
        CWT_IAT: iat,
        CWT_EXP: exp,
        CWT_HCERTL: {
            CWT_EU_DGC_V1: {
                "ver": "1.0.0",
                "nam": {
                    "fn": fn,
                    "fnt": fnt,
                    "gn": gn,
                    "gnt": gnt,
                },
                "dob": dob,
                "t": [
                    {
                        "tg": tg,
                        "tt": tt,
                        "nm": nm,
                        "sc": sc,
                        "dr": dr,
                        "tr": tr,
                        "tc": tc,
                        "co": co,
                        "is": is,
                        "ci": ci
                    }
                ]
            }
        }
    }

    return credential


def new_signed_credential(claims=None, jwk_key=None):
    """Create a Verifiable Credential in signed JWT format.
    Receives a claims object and a signing key in JWK format
    """

    if not claims:
        raise HException("Claims not specified")
    if not jwk_key:
        raise HException("Key not specified")

    # Get the issuer from the unsigned credential
    issuer_did = claims["iss"]

    # Try to resolve the Issuer and get its DID Document
    DID, name, DIDDocument, active = tf.resolver.resolveDID(issuer_did)

    # Check if the Issuer exists and return if not
    if DIDDocument is None:
        raise HException("DIDResolution failed")

    # Check if the DID inside the DIDDocument is the same as the one resolved
    if DIDDocument["id"] != issuer_did:
        raise HException("DID resolved and issuer DID do not match")

    # Get the public Key from the DID Document
    did_key = DIDDocument["verificationMethod"][0]

    # We should create the signed JWT from the "raw" credential

    # The header of the JWT, specifying the ES256K algorithm
    header = {
        "typ": "JWT",
        "alg": "ES256K",
        "kid": did_key["id"]
    }

    # Generate a JWT token, not yet signed
    token = jwt.JWT(
        algs=["ES256K"],
        header=header,
        claims=claims
    )

    # Sign the JWT with the key
    token.make_signed_token(jwk_key)

    # Serialize the token for transmission or storage
    st = token.serialize()

    token = cwt.encode(
        {"iss": "coaps://as.example", "sub": "dajiaji", "cti": "123"}, private_key
    )

    return st




################################################################################
# END HCERT definitions
################################################################################


def new_unsigned_public_credential(
    credential_name: str,
    entity_id_number: str,
    entity_name: str,
    entity_logo: str,
    entity_url: str,
    self_declarations: Sequence[str],
    issuance_time: int,
    expiration_time: int,
    issuer_did: str
):
    """Create a Claims object for a Verifiable Credential in JWT format.
    The returned object has just the plain claims object, and has to be
    signed later.
    """

    # Generate a random UUID, not related to anything in the credential
    # This is important for privacy reasons to avoid possibility of
    # correlation if the UUID is used for Revocation Lists in a blockchain
    uid = unique_id.uuid4().hex

    # Current time and expiration
    if not issuance_time:
        issuance_time = int(time.time())
    
    if not expiration_time:
        expiration_time = issuance_time + 10*24*60*60  # The token will expire in 10 days

    # Generate a template Verifiable Credential
    credential = {
        "iss": issuer_did,
        "sub": entity_id_number,
        "iat": issuance_time,
        "exp": expiration_time,
        "uuid": uid,
        "vc": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://alastria.github.io/identity/credentials/v1",
                "https://safeisland.org/.well-known/w3c-pubcred/v1"
            ],
            "type": [
                "VerifiableCredential",
                "AlastriaVerifiableCredential",
                "SafeIslandPublicCredential"
            ],
            "credentialSchema": {
                "id": "publicCredential",
                "type": "JsonSchemaValidator2018"
            },
            "credentialSubject": {
                "publicCredential": {
                    "name": credential_name,
                    "entity": {
                        "name": entity_name,
                        "logo": entity_logo,
                        "url": entity_url
                    },
                    "self_declarations": self_declarations
                },
                "issuedAt": ["redt.alastria"],
                "levelOfAssurance": 2
            }
        }
    }

    return credential


def new_signed_credential_w3c(claims=None, jwk_key=None):
    """Create a Verifiable Credential in signed JWT format.
    Receives a claims object and a signing key in JWK format
    """

    # Get the issuer from the unsigned credential
    issuer_did = claims["iss"]

    # Try to resolve the Issuer and get its DID Document
    DID, name, DIDDocument, active = tf.resolver.resolveDID(issuer_did)

    # Check if the Issuer exists and return if not
    if DIDDocument is None:
        return None

    # Check if the DID inside the DIDDocument is the same as the one resolved
    if DIDDocument["id"] != issuer_did:
        return None

    # Get the public Key from the DID Document
    did_key = DIDDocument["verificationMethod"][0]

    # We should create the signed JWT from the "raw" credential

    # The header of the JWT, specifying the ES256K algorithm
    header = {
        "typ": "JWT",
        "alg": "ES256K",
        "kid": did_key["id"]
    }

    # Generate a JWT token, not yet signed
    token = jwt.JWT(
        algs=["ES256K"],
        header=header,
        claims=claims
    )

    # Sign the JWT with the key
    token.make_signed_token(jwk_key)

    # Serialize the token for transmission or storage
    st = token.serialize()

    return st

def create_test_credentials():
    """Creates several certificates in batch.

    --- Definitions ---
    """

    # The Issuer is the Perfect Health laboratory
    issuer_did = "did:elsi:VATES-X12345678X"
    issuer_password = "ThePassword"

    # Get the JWK key from the wallet
    key = wallet.key_JWK(issuer_did, issuer_password)
    if key is None:
        print("Error: key from wallet is None!")
        return None

    ###################################################
    # Start of credential creation
    ###################################################

    declaration_name = "ESTABLECIMIENTO Covid Safe Responsable"

    self_declarations = [
        "Cumple Protocolos Sanitarios",
        "Cumple Test PcR Q Empleados",
        "Cumple Protocolos PoC"
    ]


    entities = [
        {
            "entity_name": "Meliá Salinas",
            "entity_id": "A78304516",
            "entity_url": "https://www.melia.com/es/hoteles/espana/lanzarote/melia-salinas/index.htm",
            "declaration_name": "ESTABLECIMIENTO Covid Safe Responsable",
            "self_declarations": [
                "Cumple Protocolos Sanitarios",
                "Cumple Test PcR Q Empleados",
                "Cumple Protocolos PoC"
            ],
            "issuance": "14-05-2021 00:00:01",
            "expiration": "17-05-2021 23:59:59"
        },
        {
            "entity_name": "(CICAR) Canary Islands Car",
            "entity_id": "B35051820",
            "entity_url": "https://www.cicar.com/",
            "declaration_name": "VEHICULO Covid Safe Responsable",
            "self_declarations": [
                "Cumple Protocolos Sanitarios",
                "Cumple Test PcR Q Empleados",
                "Cumple Protocolos PoC"
            ],
            "issuance": "14-05-2021 00:00:01",
            "expiration": "17-05-2021 23:59:59"
        },
        {
            "entity_name": "Lineas Romero",
            "entity_id": "B35292283",
            "entity_url": "https://www.lineasromero.com/",
            "declaration_name": "ACTIVIDAD Covid Safe Responsable",
            "self_declarations": [
                "Cumple Protocolos Sanitarios",
                "Cumple Test PcR Q Empleados",
                "Cumple Protocolos PoC"
            ],
            "issuance": "14-05-2021 00:00:01",
            "expiration": "17-05-2021 23:59:59"
        },
        {
            "entity_name": "Finca Las Higueras",
            "entity_id": "B35096346",
            "entity_url": "https://fincalashigueras.com/",
            "declaration_name": "ESTABLECIMIENTO Covid Safe Responsable",
            "self_declarations": [
                "Cumple Protocolos Sanitarios",
                "Cumple Test PcR Q Empleados",
                "Cumple Protocolos PoC"
            ],
            "issuance": "14-05-2021 00:00:01",
            "expiration": "17-05-2021 23:59:59"
        },


        {
            "entity_name": "Catlanza",
            "entity_id": "XXXXXXX",
            "entity_url": "https://www.catlanza.com/",
            "declaration_name": "ACTIVIDAD Covid Safe Responsable",
            "self_declarations": [
                "Cumple Protocolos Sanitarios",
                "Cumple Test PcR Q Empleados",
                "Cumple Protocolos PoC"
            ],
            "issuance": "14-05-2021 00:00:01",
            "expiration": "17-05-2021 23:59:59"
        },
        {
            "entity_name": "MIAC Castillo de San José y Jameos del Agua. EPEL-CACT del Cabildo de Lanzarote",
            "entity_id": "Q3500356E",
            "entity_url": "https://www.cactlanzarote.com/",
            "declaration_name": "ACTIVIDAD Covid Safe Responsable",
            "self_declarations": [
                "Cumple Protocolos Sanitarios",
                "Cumple Test PcR Q Empleados",
                "Cumple Protocolos PoC"
            ],
            "issuance": "14-05-2021 00:00:01",
            "expiration": "17-05-2021 23:59:59"
        },
        {
            "entity_name": "BODEGAS EL GRIFO",
            "entity_id": "A35053123",
            "entity_url": "https://www.elgrifo.com/",
            "declaration_name": "ACTIVIDAD Covid Safe Responsable",
            "self_declarations": [
                "Cumple Protocolos Sanitarios",
                "Cumple Test PcR Q Empleados",
                "Cumple Protocolos PoC"
            ],
            "issuance": "14-05-2021 00:00:01",
            "expiration": "17-05-2021 23:59:59"
        },
        {
            "entity_name": "GRUPO 1844",
            "entity_id": "B35062926",
            "entity_url": "https://grupo1844.com/",
            "declaration_name": "ACTIVIDAD Covid Safe Responsable",
            "self_declarations": [
                "Cumple Protocolos Sanitarios",
                "Cumple Test PcR Q Empleados",
                "Cumple Protocolos PoC"
            ],
            "issuance": "14-05-2021 00:00:01",
            "expiration": "17-05-2021 23:59:59"
        },
        {
            "entity_name": "Restaurante Brisa Marina Juan el Majorero",
            "entity_id": "B35910827",
            "entity_url": "http://restaurantebrisamarina.es/",
            "declaration_name": "ACTIVIDAD Covid Safe Responsable",
            "self_declarations": [
                "Cumple Protocolos Sanitarios",
                "Cumple Test PcR Q Empleados",
                "Cumple Protocolos PoC"
            ],
            "issuance": "14-05-2021 00:00:01",
            "expiration": "17-05-2021 23:59:59"
        },
        {
            "entity_name": "H Smith Solutions",
            "entity_id": "J76158815",
            "entity_url": "https://www.hsmith.es/",
            "declaration_name": "ACTIVIDAD Covid Safe Responsable",
            "self_declarations": [
                "Cumple Protocolos Sanitarios",
                "Cumple Test PcR Q Empleados",
                "Cumple Protocolos PoC"
            ],
            "issuance": "14-05-2021 00:00:01",
            "expiration": "17-05-2021 23:59:59"
        },

    ]


    for entity in entities:
        entity_id = "did:elsi:VATES-" + entity["entity_id"]
        issuance_time = time.mktime(time.strptime(entity["issuance"], "%d-%m-%Y %H:%M:%S"))
        expiration_time = time.mktime(time.strptime(entity["expiration"], "%d-%m-%Y %H:%M:%S"))

        claims = new_unsigned_public_credential(
            credential_name = entity["declaration_name"],
            entity_id_number = entity_id,
            entity_name = entity["entity_name"],
            entity_logo = f"img/pubcred/{entity['entity_id']}.png",
            entity_url = entity["entity_url"],
            issuance_time= issuance_time,
            expiration_time= expiration_time,
            self_declarations = entity["self_declarations"],
            issuer_did = issuer_did
        )

        st = new_signed_credential(
            claims=claims,
            jwk_key=key
        )

        if st is None:
            print(f"Error creating signed credential")
            return

        # Save the Credential in the database, indexed by its unique id
        uuid = new_record(uuid=claims["uuid"], ctype="PUBCRED", sformat="JWT", cert=st)
        print(f"New certificate created: {uuid}, Credential Schema: {claims['vc']['credentialSchema']['id']}")


    print("All very well")
    return







def m_new_public_certificate(
    credential_name: str,
    entity_id_number: str,
    entity_name: str,
    entity_logo: str,
    entity_url: str,
    self_declaration1: str,
    self_declaration2: str,
    self_declaration3: str,
    self_declaration4: str,
    issuance_time: str,
    expiration_time: str,
    issuer_did: str,
    issuer_password: str
):
    """Creates a new certificate.

    --- Definitions ---
    {"name": "credential_name", "prompt": "Credential name first name", "default": "ESTABLECIMIENTO Covid Safe Responsable"}
    {"name": "entity_id_number", "prompt": "Subject DID", "default": "did:elsi:VATES-A78304516"}
    {"name": "entity_name", "prompt": "Name of subject entity", "default": "Meliá Salinas"}
    {"name": "entity_logo", "prompt": "Logo image in Base64 format", "default": "TheLogo"}
    {"name": "entity_url", "prompt": "Website", "default": "https://www.melia.com/es/hoteles/espana/lanzarote/melia-salinas/index.htm"}
    {"name": "self_declaration1", "prompt": "Declaration 1", "default": "Cumple Protocolos Sanitarios"}
    {"name": "self_declaration2", "prompt": "Declaration 2", "default": "Cumple Test PcR Q Empleados"}
    {"name": "self_declaration3", "prompt": "Declaration 3", "default": "Cumple Protocolos PoC"}
    {"name": "self_declaration4", "prompt": "Declaration 4", "default": ""}
    {"name": "issuance_time", "prompt": "Issuance time, format YYYY-MM-DD HH:mm:ss", "default": "14-05-2021 00:00:01"}
    {"name": "expiration_time", "prompt": "Expiration time, format YYYY-MM-DD HH:mm:ss", "default": "17-05-2021 23:59:59"}
    {"name": "issuer_did", "prompt": "DID of Issuer", "default": "did:elsi:VATES-X12345678X"}
    {"name": "password", "prompt": "Password of Issuer", "default": "ThePassword"}
    """

    # Convert string times to seconds since epoch
    issuance_time = time.mktime(time.strptime(issuance_time, "%d-%m-%Y %H:%M:%S"))
    expiration_time = time.mktime(time.strptime(expiration_time, "%d-%m-%Y %H:%M:%S"))

    # Build the self-declarations array
    self_declarations = []
    if len(self_declaration1) > 0:
        self_declarations.append(self_declaration1)
    if len(self_declaration2) > 0:
        self_declarations.append(self_declaration2)
    if len(self_declaration3) > 0:
        self_declarations.append(self_declaration3)
    if len(self_declaration4) > 0:
        self_declarations.append(self_declaration4)

    # Create a credential with the credential data
    claims = new_unsigned_public_credential(
        credential_name = credential_name,
        entity_id_number = entity_id_number,
        entity_name = entity_name,
        entity_logo = entity_logo,
        entity_url = entity_url,
        self_declarations = self_declarations,
        issuance_time= issuance_time,
        expiration_time= expiration_time,
        issuer_did = issuer_did
    )    

    # Get the JWK key from the wallet
    key = wallet.key_JWK(issuer_did, issuer_password)
    if key is None:
        print("Error: key from wallet is None!")
        return None
    print(type(key))

    # Create a signed Verifiable Credential in serialized JWT/JWS format
    st = new_signed_credential(
        claims=claims,
        jwk_key=key
    )

    # Save the Credential in the database, indexed by its unique id
    hash = new_record(uuid=claims["uuid"], ctype="PUBCRED", sformat="JWT", cert=st)
    print(f"New certificate created: {st}")


def m_certificate(
        uuid: str):
    """Gets certificate from its Unique ID.

    --- Definitions ---
    {"name": "uuid", "prompt": "Unique number of certificate", "default": "None"}
    """

    # Check if unique ID was provided
    if uuid == "None":
        print("Error: Must supply a Unique ID")
        return

    # Get the serialized JWT from the database
    cert = record(uuid)
    if cert is None:
        print(f"Certificate not found")
        return

    claims = verify_cert_token(cert)
    if claims is None:
        print("Verification of token failed")
        return

    payl = claims

    print(cert)
    print(json.dumps(payl, indent=6))


def m_list_certificates():
    """List PubCred certificates

    """

    certs = list_records()
    for cert in certs:
        print(f"\nUnique ID: {cert['uuid']}")
        print(f"   {cert['cert']}")


def verify_cert_token(cert_token:str) -> dict:
    """In order to verify the signature of the JWT, we need first to get the public key that was used.
    The JWT is now in serialized format, so we need:
    1. Deserialize the JWT without verifying it (we do not yet have the public key)
    2. Get the 'kid' property from the header (the JOSE header of the JWT)
    3. The 'kid' has the format did#id where 'did' is the DID of the issuer and 'id' is the 
        identifier of the key in the DIDDocument associated to the DID
    4. Perform resolution of the DID of the issuer
    5. Get the public key specified inside the DIDDocument
    6. Verify the JWT using the public key associated to the DID
    7. Verify that the DID in the 'iss' field of the JWT payload is the same as the one that
        signed the JWT
    """

    # 1. Deserialize the JWT without verifying it (we do not yet have the public key)
    cert_obj = jwt.JWT()
    cert_obj.deserialize(jwt=cert_token)
 
    # Get the protected header of the JWT
    header = cert_obj.token.jose_header

    # 2. Get the 'kid' property from the header (the JOSE header of the JWT)
    key_id = str(header["kid"])

    # 3. The 'kid' has the format did#id where 'did' is the DID of the issuer and 'id' is the 
    #     identifier of the key in the DIDDocument associated to the DID
    key_components = key_id.split("#")
    if len(key_components) != 2:
        print(f"KeyID in JOSE header invalid: {header}")
        return None

    # Get the DID component
    DID = key_components[0]

    # 4. Perform resolution of the DID of the issuer, and get the public key
    _DID, name, didDoc, active = tf.resolver.resolveDID(DID)
    if didDoc is None:
        print(f"No DIDDoc found for DID: {DID}")
        return None

    # 5. Get the public key specified inside the DIDDocument
    keys = didDoc["verificationMethod"]
    publicKeyJwk = None
    for key in keys:
        if key["id"] == key_id:
            publicKeyJwk = key["publicKeyJwk"]

    if publicKeyJwk is None:
        print(f"Key ID not found in DIDDoc: {key_id}")
        return None

    jwk_key = jwk.JWK(**publicKeyJwk)

    # 6. Verify the JWT using the public key associated to the DID
    cert_obj = jwt.JWT(
        jwt=cert_token,
        key=jwk_key,
        algs=["ES256K"]
    )

    # 7. Verify that the DID in the 'iss' field of the JWT payload is the same as the one that
    #     signed the JWT
    claims = json_decode(cert_obj.claims)
    if claims["iss"] != DID:
        print(f"Token issuer is not the same as specified in the header")
        return None

    return claims

def verify_cert_token_debug(cert_token:str) -> dict:
    """Help debug a given JWT token

    --- Definitions ---
    {"name": "cert_token", "prompt": "Token to debug", "default": "None"}
    """

    # 1. Deserialize the JWT without verifying it (we do not yet have the public key)
    cert_obj = jwt.JWT()
    print("Created JWT object")
    cert_obj.deserialize(jwt=cert_token)
    print("Deserialized")
 
    # Get the protected header of the JWT
    header = cert_obj.token.jose_header

    # 2. Get the 'kid' property from the header (the JOSE header of the JWT)
    key_id = str(header["kid"])

    # 3. The 'kid' has the format did#id where 'did' is the DID of the issuer and 'id' is the 
    #     identifier of the key in the DIDDocument associated to the DID
    key_components = key_id.split("#")
    if len(key_components) != 2:
        print(f"KeyID in JOSE header invalid: {header}")
        return None

    # Get the DID component
    DID = key_components[0]

    # 4. Perform resolution of the DID of the issuer, and get the public key
    _DID, name, didDoc, active = tf.resolver.resolveDID(DID)
    if didDoc is None:
        print(f"No DIDDoc found for DID: {DID}")
        return None

    print(f"DID resolved: {DID}")

    # 5. Get the public key specified inside the DIDDocument
    keys = didDoc["verificationMethod"]
    publicKeyJwk = None
    for key in keys:
        if key["id"] == key_id:
            publicKeyJwk = key["publicKeyJwk"]

    if publicKeyJwk is None:
        print(f"Key ID not found in DIDDoc: {key_id}")
        return None
    print(f"Resolved key:")
    debug(publicKeyJwk)

    jwk_key = jwk.JWK(**publicKeyJwk)

    # 6. Verify the JWT using the public key associated to the DID
    cert_obj = jwt.JWT(
        jwt=cert_token,
        key=jwk_key,
        algs=["ES256K"]
    )

    # 7. Verify that the DID in the 'iss' field of the JWT payload is the same as the one that
    #     signed the JWT
    claims = json_decode(cert_obj.claims)
    if claims["iss"] != DID:
        print(f"Token issuer is not the same as specified in the header")
        return None

    return claims

















