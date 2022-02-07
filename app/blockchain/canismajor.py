import os
import logging
import hashlib
import sqlite3
from sqlite3.dbapi2 import Connection
import uuid as unique_id
import time

# For the data models
from typing import Dict, Optional, cast
from pydantic import BaseModel, BaseSettings

from web3 import Web3
from web3.types import TxReceipt

from blockchain import redt as b
from blockchain import wallet, didutils, redt
from blockchain import tolar_hashnet

from hexbytes import HexBytes

try:
    from devtools import debug
except ImportError:
    def debug(*arg):
        pass

# The settings for the system
from settings import settings

# Initialize logging
log = logging.getLogger(__name__)

DATABASE_FILE = "canismajor.sqlite"
DATABASE_NAME = os.path.join(settings.DATABASE_DIR, DATABASE_FILE)

drop_table_script = """
DROP TABLE IF EXISTS stamping;
"""

create_table_script = """
CREATE TABLE IF NOT EXISTS stamping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ngsi_id TEXT NOT NULL,
    ngsi_value TEXT NOT NULL,
    ngsi_receipt TEXT NOT NULL
);
"""

def create_db() -> Connection:
    """Create the table if it does not exist
    """
    db = get_db()
    db.executescript(create_table_script)
    return db

def get_db() -> Connection:
    """Get a database handle
    """
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
    db.executescript(drop_table_script)
    print(f"Database schema created")

    return db

# Connect with the blockchain provider
provider=settings.BLOCKCHAIN_NODE_IP
w3 = b.setup_provider(provider)

# The path to the contracts deployment artifacts
Timestamper_full_path = os.path.join(settings.CONTRACTS_OUTPUT_DIR, "Timestamper")
Timestamper = b.bind_contract(Timestamper_full_path)

owner_account = "Timestamper"
owner_password = "ThePassword"

tol = tolar_hashnet.acc
tol.set_contract_wrapper(Timestamper)

def hash_string(text: str) -> bytes:
    """Calculate a hash of a string"""
    btext = bytes(text, "utf-8")
    h = hashlib.sha256()
    h.update(btext)
    d = h.digest()
    return d

import orjson

def default(obj):
    if isinstance(obj, HexBytes):
        return obj.hex()
    raise TypeError

def timestamp(id: str, value: dict) -> dict:
    """Timestamp the hashes of an id and value.
    """

    # Order the dict keys, to make the serialization repeatable
    sorted_value = sorted(value.items())
    print(sorted_value)


    # Serialize the dict, ordering the keys lexicographically 
    sorted_dict = orjson.dumps(value, option=orjson.OPT_SORT_KEYS)

    # Hash the "id" (of type string)
    id_hash = Web3.toInt(hash_string(id))

    # Hash the serialized version of the received dict object
    h = hashlib.sha256()
    h.update(sorted_dict)
    d = h.digest()
    value_hash = Web3.toInt(d)

    # Get the JWK key from the wallet
    owner_key = wallet.get_account(owner_account, owner_password)
    if owner_key is None:
        raise Exception("Invalid account")

    private_key = owner_key.privateKey

    # Get the contract wrapper
    contract_fun = Timestamper.functions.timestamp(id_hash, value_hash)

    # Execute the transaction
    success, tx_receipt, tx_hash = b.send_signed_tx(
        contract_fun, private_key)

    # Execute transaction in Tolar Hashnet
    # tx_data = tol.get_transaction_data(id_hash, value_hash)
    # tol_receipt = tol.SendExecuteFunctionTransaction(tx_data)
    tol_receipt = None

    # Convert the transaction receipt to a standard python dict
    receipt = receipts_as_vc(tx_receipt, tol_receipt)

    serialized_receipt = orjson.dumps(receipt, default=default)

    # Store the data in the local database
    db = get_db()
    db.execute(
        'REPLACE INTO stamping (ngsi_id, ngsi_value, ngsi_receipt) VALUES (?, ?, ?)',
        (id, sorted_dict, serialized_receipt)
    )
    # Commit database
    db.commit()

    return receipt

def checktimestamp() -> bool:
    """Check if smart contract is accessible.

    --- Definitions ---
    """

    hash1 = 0x555555555555
    hash2 = 0x88888888888888888

    # Call the timestamp function as a call, not transaction
    return_code = Timestamper.functions.timestamp(hash1, hash2).call()

    print("OK")
    return True

# For the menu operations
def m_timestamp():
    """Timestamp a hash.

    --- Definitions ---
    """

    # Get the JWK key from the wallet
    owner_key = wallet.get_account(owner_account, owner_password)
    if owner_key is None:
        raise Exception("Invalid account")

    hash1 = 0x555555555555
    hash2 = 0x88888888888888888
    private_key = owner_key.privateKey

    # Get the contract wrapper
    contract_fun = Timestamper.functions.timestamp(hash1, hash2)
    success, tx_receipt, tx_hash = b.send_signed_tx(
        contract_fun, private_key)

    # Convert the transaction receipt to a standard python dict
    receipt = receipt_as_vc(tx_receipt)

    return receipt

def list_one_item(ngsi_id: str):
    """List one item.

    --- Definitions ---
    {"name": "ngsi_id", "prompt": "Id of the item"}
    """

    db = get_db()

    all_items = db.execute('SELECT * FROM stamping WHERE ngsi_id = ?', (ngsi_id,)).fetchall()
    if len(all_items) == 0:
        return {}
    
    item = all_items[-1]
    

    item_d = {
        "id": item["ngsi_id"],
        "value": orjson.loads(item["ngsi_value"]),
        "receipt": orjson.loads(item["ngsi_receipt"])
    }

    return item_d

def list_all():
    """List all items.

    --- Definitions ---
    """

    db = get_db()

    items = db.execute('SELECT * FROM stamping ORDER BY id').fetchall()
    list_accumulator = []
    for item in items:
        list_accumulator.append({k: item[k] for k in item.keys()})

    return list_accumulator

    
def get_receipt(tx_hash):
    """Get the transaction receipt from the blockchain, and
    create a Claims object for a Verifiable Credential in JWT format.
    The returned object has just the plain claims object, and has to be
    signed later.
    """

    # Get the raw transaction receipt from the blockchain
    raw_receipt = redt.get_transaction_receipt(tx_hash)

    # And convert to an unsigned Verifiable Credential
    receipt = receipt_as_vc2(raw_receipt)

    return receipt

class ReceiptModel(BaseModel):
    iss: str
    sub: str
    iat: int
    exp: int
    uuid: int


def receipt_as_vc(tx_receipt: TxReceipt) -> dict:
    """Convert a raw tx receipt to an unsigned Verifiable Credential"""

    # Generate a random UUID, not related to anything in the credential
    uid = unique_id.uuid4().hex

    # Current time and expiration
    now = int(time.time())
    one_year = 365*24*60*60
    exp = now + one_year  # The token will expire in 365 days

    debug(tx_receipt)
    logs = []
    for item in tx_receipt["logs"][0]["topics"]:
        logs.append(Web3.toHex(item))

    # Generate Verifiable Credential
    credential = {
        "iss": "did:elsi:VATES-B87307609",
        "sub": "did:elsi:VATES-B87307609",
        "iat": now,
        "exp": exp,
        "uuid": uid,
        "vc": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://alastria.github.io/identity/credentials/v1",
                "https://www.fiware.org/.well-known/ngsiv2/v1"
            ],
            "type": [
                "VerifiableCredential",
                "NGSIv2ReceiptCredential"
            ],
            "credentialSchema": {
                "id": "NGSIv2ReceiptCredential",
                "type": "JsonSchemaValidator2018"
            },
            "credentialSubject": {
                "NGSIv2ReceiptCredential": {
                    "issuedAt": ["redt.alastria"],
                    "levelOfAssurance": 2,
                    "blockHash": Web3.toHex(tx_receipt["blockHash"]),
                    "blockNumber": tx_receipt["blockNumber"],
                    "transactionHash": Web3.toHex(tx_receipt["transactionHash"]),
                    "transactionIndex": tx_receipt["transactionIndex"],
                    "from": tx_receipt["from"],
                    "to": tx_receipt["to"],
                    "logs": logs
                }
            }
        }
    }

    return credential

def receipt_as_vc2(tx_receipt: dict) -> dict:
    """Convert a raw tx receipt to an unsigned Verifiable Credential"""

    # Generate a random UUID, not related to anything in the credential
    uid = unique_id.uuid4().hex

    # Current time and expiration
    now = int(time.time())
    one_year = 365*24*60*60
    exp = now + one_year  # The token will expire in 365 days

    debug(tx_receipt)
    logs = []
    for item in tx_receipt["logs"][0]["topics"]:
        logs.append(item)

    # Generate Verifiable Credential
    credential = {
        "iss": "did:elsi:VATES-B87307609",
        "sub": "did:elsi:VATES-B87307609",
        "iat": now,
        "exp": exp,
        "uuid": uid,
        "vc": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://alastria.github.io/identity/credentials/v1",
                "https://www.fiware.org/.well-known/ngsiv2/v1"
            ],
            "type": [
                "VerifiableCredential",
                "AlastriaVerifiableCredential",
                "NGSIv2ReceiptCredential"
            ],
            "credentialSchema": {
                "id": "NGSIv2ReceiptCredential",
                "type": "JsonSchemaValidator2018"
            },
            "credentialSubject": {
                "NGSIv2ReceiptCredential": {
                    "issuedAt": "redt.alastria",
                    "levelOfAssurance": 2,
                    "blockHash": tx_receipt["blockHash"],
                    "blockNumber": tx_receipt["blockNumber"],
                    "transactionHash": tx_receipt["transactionHash"],
                    "transactionIndex": tx_receipt["transactionIndex"],
                    "from": tx_receipt["from"],
                    "to": tx_receipt["to"],
                    "logs": logs
                },
            }
        }
    }

    return credential


def receipts_as_vc(tx_receipt: TxReceipt, tol_receipt: dict) -> dict:
    """Convert a raw tx receipt to an unsigned Verifiable Credential"""

    # Generate a random UUID, not related to anything in the credential
    uid = unique_id.uuid4().hex

    # Current time and expiration
    now = int(time.time())
    one_year = 365*24*60*60
    exp = now + one_year  # The token will expire in 365 days

    logs = []
    for item in tx_receipt["logs"][0]["topics"]:
        logs.append(Web3.toHex(item))

    cred_redt = {
        "issuedAt": "redt.alastria",
        "levelOfAssurance": 2,
        "blockHash": Web3.toHex(tx_receipt["blockHash"]),
        "blockNumber": tx_receipt["blockNumber"],
        "transactionHash": Web3.toHex(tx_receipt["transactionHash"]),
        "transactionIndex": tx_receipt["transactionIndex"],
        "from": tx_receipt["from"],
        "to": tx_receipt["to"],
        "logs": logs,
    }

    NGSIv2ReceiptCredential = [cred_redt]

    if tol_receipt:
        logs = []
        for item in tol_receipt["logs"][0]["topics"]:
            logs.append("0x"+item)

        cred_tol = {
            "issuedAt": "tolar.hashnet",
            "levelOfAssurance": 2,
            "blockHash": tol_receipt["blockHash"],
            "blockNumber": int(tol_receipt["blockIndex"]),
            "transactionHash": tol_receipt["transactionHash"],
            "from": tol_receipt["senderAddress"],
            "to": tol_receipt["receiverAddress"],
            "logs": logs,
        }

        NGSIv2ReceiptCredential.append(cred_tol)

    # Generate Verifiable Credential
    credential = {
        "iss": "did:elsi:VATES-B87307609",
        "sub": "did:elsi:VATES-B87307609",
        "iat": now,
        "exp": exp,
        "uuid": uid,
        "vc": {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://alastria.github.io/identity/credentials/v1",
                "https://www.fiware.org/.well-known/ngsiv2/v1"
            ],
            "type": [
                "VerifiableCredential",
                "NGSIv2ReceiptCredential"
            ],
            "credentialSchema": {
                "id": "NGSIv2ReceiptCredential",
                "type": "JsonSchemaValidator2018"
            },
            "credentialSubject": {
                "NGSIv2ReceiptCredential": NGSIv2ReceiptCredential
            }
        }
    }

    return credential
