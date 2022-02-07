import os
import time
import sqlite3
import json
from sqlite3.dbapi2 import Connection
from eth_utils.crypto import keccak
from hexbytes import HexBytes
from dataclasses import dataclass
from pprint import pprint

from pydantic import BaseModel
from typing import Optional, Tuple

from web3.main import Web3

from blockchain import trustframework as tf
from blockchain import wallet

from jwcrypto import jwt, jwk, jws
from jwcrypto.common import base64url_decode, base64url_encode, json_decode, json_encode


DATABASE_DIR = os.getcwd()
DATABASE_NAME = os.path.join(DATABASE_DIR, "certificates.sqlite")

table_schema = """
DROP TABLE IF EXISTS certificate;

CREATE TABLE certificate (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  diag_id TEXT UNIQUE NOT NULL,
  hash TEXT UNIQUE NOT NULL,
  cert TEXT NOT NULL
);
"""


def get_db() -> Connection:
    db = sqlite3.connect(DATABASE_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db


def erase_db() -> Connection:
    """Erase the table

    """

    # Connect the database (in case of SQLite just opens the file)
    db = get_db()

    # Erase and create the table from scratch
    print(f"\n==> Creating the database schema")
    db.executescript(table_schema)
    print(f"Database schema created")

    return db


def new_certificate(diag_id: str, certificate: str) -> HexBytes:

    db = get_db()

    # Calculate the hash
    hash = Web3.keccak(text=certificate)

    db.execute(
        'REPLACE INTO certificate (diag_id, hash, cert) VALUES (?, ?, ?)',
        (diag_id, hash.hex(), certificate)
    )
    # Commit database, just in case
    db.commit()

    # Return certificate hash to caller
    return hash


def certificate(diag_id: str) -> str:

    db = get_db()

    cert = db.execute(
        'SELECT * FROM certificate WHERE diag_id = ?', (diag_id,)
    ).fetchone()

    if cert is None:
        return None

    # Get the serialized format of the certificate
    cert = cert["cert"]

    return cert


def list_certificates():

    db = get_db()

    certs = db.execute('SELECT * FROM certificate ORDER BY diag_id').fetchall()

    return certs


def new_signed_credential(iss=None, sub=None, certificate=None, password=None):

    # Try to resolve the Issuer and get its DID Document
    DID, name, DIDDocument, active = tf.resolver.resolveDID(iss)

    # Check if the Issuer exists and return if not
    if DIDDocument is None:
        return None

    # Get the public Key from the DID Document
    did_key = DIDDocument["publicKey"][0]

    # Generate a template Verifiable Credential
    now = int(time.time())
    validity = 5*24*60*60  # The token will expire in 6 days
    credential = {
        "iss": iss,
        "sub": sub,
        "iat": now,
        "exp": now + validity,
        "nbf": now,
        "vc": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://alastria.github.io/identity/credentials/v1",
                "https://safeisland.org/.well-known/christmasbasket/v1"
            ],
            "type": [
                "VerifiableCredential",
                "AlastriaVerifiableCredential",
                "ChristmasBasket"
            ],
            "credentialSubject": {
                "issuedAt": "alastria.redt",
                "levelOfAssurance": 2,
                "christmasBasket": {
                }
            }
        }
    }

    # Fill the "christmasBasket" field of the Verifiable Credential
    credential["vc"]["credentialSubject"]["christmasBasket"] = certificate

    credential = json.dumps(credential, ensure_ascii=False, sort_keys=False)

    # The header of the JWT
    header = {
        "typ": "JWT",
        "alg": "ES256K",
        "kid": did_key["id"]
    }

    # Generate a JWT token, not yet signed
    token = jwt.JWT(
        algs=["ES256K"],
        header=header,
        claims=credential
    )

    # Get the JWK key from the wallet
    key = wallet.key_JWK(DID, password)
    if key is None:
        return None
    print(type(key))

    # Sign the JWT with the key
    token.make_signed_token(key)

    # Serialize the token for transmission or storage
    st = token.serialize()

    return st


def new_unsigned_credential(
    product_id: str,
    product_name: str,
    product_description: str,
    declaration_uri: str,
    declaration_hash: str
):

    ct = {
        "id": product_id,
        "product": product_name,
        "description": product_description,
        "declaration": {
            "uri": declaration_uri,
            "hash": declaration_hash
        } 
    }

    return ct


def m_new_certificate(
    producer_did: str,
    product_id: str,
    product_name: str,
    product_description: str,
    declaration_uri: str,
    declaration_hash: str
):
    """Creates a new certificate.

    --- Definitions ---
    {"name": "producer_did", "prompt": "Producer DID", "default": "did:elsi:VATES-Q0901252G"}
    {"name": "product_id", "prompt": "Product unique ID", "default": "P375865"}
    {"name": "product_name", "prompt": "Product name", "default": "Lechazo"}
    {"name": "product_description", "prompt": "Product description", "default": "Descripcion del producto"}
    {"name": "declaration_uri", "prompt": "Declaration URI", "default": "http://www.cestablockchain.com/declaraciones/declaracion.pdf"}
    {"name": "declaration_hash", "prompt": "Declaration hash", "default": "No_default"}
    """

    # Create a credential with the diagnostic data
    ct = new_unsigned_credential(
        product_id,
        product_name,
        product_description,
        declaration_uri,
        declaration_hash
    )

    # Create a signed Verifiable Credential in serialized JWT/JWS format
    # This is a Self Declaration, so issuer and subject are the same: the producer
    st = new_signed_credential(
        iss=producer_did,
        sub=producer_did,
        certificate=ct,
        password="ThePassword"
    )

    # Save the Credential in the database, indexed by the product_id
    hash = new_certificate(product_id, st)
    print(f"New certificate created: {st}")


def verify_cert_token(cert_token:str) -> dict:

    # In order to verify the signature of the JWT, we need first to get the public key that was used
    # The JWT is now in serialized format, so we need:
    # 1. Deserialize the JWT without verifying it (we do not yet have the public key)
    # 2. Get the 'kid' property from the header (the JOSE header of the JWT)
    # 3. The 'kid' has the format did#id where 'did' is the DID of the issuer and 'id' is the 
    #     identifier of the key in the DIDDocument associated to the DID
    # 4. Perform resolution of the DID of the issuer
    # 5. Get the public key specified inside the DIDDocument
    # 6. Verify the JWT using the public key associated to the DID
    # 7. Verify that the DID in the 'iss' field of the JWT payload is the same as the one that
    #     signed the JWT

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
    keys = didDoc["publicKey"]
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


def m_certificate(
        diag_id: str):
    """Gets certificate from its DIAGNOSTIC_NUMBER.

    --- Definitions ---
    {"name": "diag_id", "prompt": "Diagnostic number", "default": "LE4RDS"}
    """

    # Get the serialized JWT from the database
    cert = certificate(diag_id)
    if cert is None:
        print(f"Certificate not found")
        return

    claims = verify_cert_token(cert)
    if claims is None:
        print("Verification of token failed")
        return

    payl = claims

    print(json.dumps(payl, indent=3, ensure_ascii=False))


def m_list_certificates():
    """List Christmas certificates

    """

    certs = list_certificates()
    for cert in certs:
        print(f"\nDiagID: {cert['diag_id']}")
        print(f"   {cert['cert']}")


######################################################################
# CREATE IDENTITIES
######################################################################

def m_create_identities():
    """Create identities in the Trust Framework hierarchy."""

    # Retrieve the Alastria account for node "ala", using the password from deployment (not for production)
    print(f"\n==> Retrieve Alastria account")
    Alastria_account = wallet.account(
        "Alastria", "ThePassword")
    alakey = Alastria_account.key
    print(f"Done")


    ################################
    # IGP Lechazo
    print(f"\n==> Creating the IGP Lechazo identity")

    DID = "did:elsi:VATES-Q0901252G"
    parent_node = "ala"
    this_node = "igplechazodecastillayleon"
    website = "https://igplechazodecastillayleon.es"
    commercial_name = "IGP Lechazo - C.R. Lechazo de Castilla y Leon"

    didDoc = tf.create_DID(DID, parent_node, this_node, website, commercial_name, Alastria_account)
    if didDoc is not None:
        pprint(didDoc, indent=3)

    ################################
    # Valdecuevas
    print(f"\n==> Creating the Valdecuevas identity")

    DID = "did:elsi:VATES-B47027982"
    parent_node = "ala"
    this_node = "valdecuevas"
    website = "https://www.valdecuevas.es"
    commercial_name = "GRUPO VALDECUEVAS AGRO, SLU"

    didDoc = tf.create_DID(DID, parent_node, this_node, website, commercial_name, Alastria_account)
    if didDoc is not None:
        pprint(didDoc)

    ################################
    # Entrepinares
    print(f"\n==> Creating the Entrepinares identity")

    DID = "did:elsi:VATES-A47037296"
    parent_node = "ala"
    this_node = "entrepinares"
    website = "https://www.entrepinares.es"
    commercial_name = "QUESERIAS ENTREPINARES S.A.U."

    didDoc = tf.create_DID(DID, parent_node, this_node, website, commercial_name, Alastria_account)
    if didDoc is not None:
        pprint(didDoc)

    ################################
    # Don Saturnino
    print(f"\n==> Creating the Don Saturnino identity")

    DID = "did:elsi:VATES-B37469509"
    parent_node = "ala"
    this_node = "donsaturnino"
    website = "http://donsaturnino.es"
    commercial_name = "INCAHER-DON SATURNINO S.L"

    didDoc = tf.create_DID(DID, parent_node, this_node, website, commercial_name, Alastria_account)
    if didDoc is not None:
        pprint(didDoc)

    ################################
    # DENOMINACIÓN DE ORIGEN LEÓN
    print(f"\n==> Creating the DENOMINACIÓN DE ORIGEN LEÓN identity")

    DID = "did:elsi:VATES-Q2400564G"
    parent_node = "ala"
    this_node = "doleon"
    website = "https://www.doleon.es/"
    commercial_name = "DENOMINACION DE ORIGEN LEON"

    didDoc = tf.create_DID(DID, parent_node, this_node, website, commercial_name, Alastria_account)
    if didDoc is not None:
        pprint(didDoc)


######################################################################
# CREATE CREDENTIALS
######################################################################

def m_create_credentials():
    """Create Christmas credentials."""

    ################################
    # Aceite Pago de ValdeCuevas
    print(f"\n==> Creating the Aceite Pago de ValdeCuevas credential")

    producer_did = "did:elsi:VATES-B47027982"
    product_id = "pagodevaldecuevas.valdecuevas.ala"
    product_name = "Aceite Pago de ValdeCuevas"
    product_description = "Aceite procedente de nuestros propios olivos arbequinos cultivados en el Pago que le da nombre"
    declaration_uri = "http://www.cestablockchain.com/pago.pdf"
    declaration_hash = "80b30bd3f43df19fcf0eba4d0e85cbf1a55d3a6b9f5f7d38e8aa53a8639d6188"

    m_new_certificate(
        producer_did,
        product_id,
        product_name,
        product_description,
        declaration_uri,
        declaration_hash
    )

    ################################
    # Jamon don Saturnino
    print(f"\n==> Creating the Jamon don Saturnino credential")

    producer_did = "did:elsi:VATES-B37469509"
    product_id = "silviarivera.donsaturnino.ala"
    product_name = "Jamón de Cebo Ibérico Silvia Ribera"
    product_description = "Jamón de Cebo Ibérico 50% Raza Ibérica. Marca Silvia Ribera"
    declaration_uri = "https://www.cestablockchain.com/pdf/jamon_guijuelo.pdf"
    declaration_hash = "a3966107ac17ea95dddd4ef69166d122c299e71a7a53fafaee63f1ba1e214517"

    m_new_certificate(
        producer_did,
        product_id,
        product_name,
        product_description,
        declaration_uri,
        declaration_hash
    )

    ################################
    # Lechazo IGP
    print(f"\n==> Creating the Lechazo IGP credential")

    producer_did = "did:elsi:VATES-Q0901252G"
    product_id = "cubillodeojeda.igplechazodecastillayleon.ala"
    product_name = "Lechazo de I.G.P."
    product_description = "Lechazo IGP. Ganadero: Jose Luis Fraile Báscones. Ubicación ganadería: Cubillo de Ojeda"
    declaration_uri = "https://www.cestablockchain.com/pdf/lechazoIGP.pdf"
    declaration_hash = "d361660473429c25aee2161854523caeba18d0ea82ce51576a4295e8756f9226"

    m_new_certificate(
        producer_did,
        product_id,
        product_name,
        product_description,
        declaration_uri,
        declaration_hash
    )


