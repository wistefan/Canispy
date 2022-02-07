import os
import sqlite3
import json
from hexbytes import HexBytes
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_keys.datatypes import PrivateKey, PublicKey
from jwcrypto.jwk import JWK
from pydantic import BaseModel
from typing import Optional, Tuple
from jwcrypto import jwt, jwk, jws
from jwcrypto.common import base64url_decode, base64url_encode

from settings import settings

DATABASE_FILE = "wallet.sqlite"

DATABASE_NAME = os.path.join(settings.DATABASE_DIR, DATABASE_FILE)

accounts_schema = """
DROP TABLE IF EXISTS testaccount;

CREATE TABLE testaccount (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  address TEXT UNIQUE NOT NULL,
  publickey TEXT NOT NULL,
  privatekey TEXT NOT NULL
);
"""

def get_wallet_db():
    db = sqlite3.connect(DATABASE_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db

def erase_wallet_db():
    """WARNING !!! Erases ALL wallet accounts.

    --- Definitions ---
    """

    # Connect the database (in case of SQLite just opens the file)
    db = get_wallet_db()

    # Erase and create the table from scratch
    print(f"\n==> Creating the database schema")
    db.executescript(accounts_schema)
    print(f"Database schema created")

    return db

def create_and_save_account(account_name, password):

    db = get_wallet_db()

    # Generate the private key using Ethereum methods
    acc = Account.create(extra_entropy="Alastria is the first Public-Permissioned Blockchain Network")
    address = acc.address
    publicKey = PublicKey.from_private(acc._key_obj).to_hex()

    # Encrypt the private key and prepare for saving it
    key_encrypted = acc.encrypt(password)
    key_encrypted = json.dumps(key_encrypted)

    print(f"Saving {address} and its private key in database)")
    db.execute(
        'REPLACE INTO testaccount (name, address, publickey, privatekey) VALUES (?, ?, ?, ?)',
        (account_name, address, publicKey, key_encrypted)
    )
    # Commit database, just in case
    db.commit()

    # Return account to caller
    return acc


def account_from_name(name, password):
    """Get the account with the specified name."""
    db = get_wallet_db()

    account = db.execute(
        'SELECT * FROM testaccount WHERE name = ?', (name,)
    ).fetchone()

    if account is None:
        return None, None

    private_key = Account.decrypt(account["privatekey"], password)

    return account["address"], private_key

def account_from_address(address):
    """Get the account with the specified address."""

    db = get_wallet_db()

    account = db.execute(
        'SELECT * FROM testaccount WHERE address = ?', (address,)
    ).fetchone()

    if account is None:
        return None, None

    return account["name"], account["publickey"]


############################################################
# MENU functions

class AccountData(BaseModel):
    address: HexBytes
    publicKey: HexBytes
    privateKey: Optional[HexBytes] = None

def generate_private_key(entropy: str = "Alastria is the first Public-Permissioned Blockchain Network") -> AccountData:

    # Generate the private key using Ethereum methods
    eth_acc = Account.create(extra_entropy=entropy)

    # Get the address, public key and private key into the AccountData structure,
    # which is independent from eth_account.Account
    account = AccountData(
        address = eth_acc.address,
        publicKey = PublicKey.from_private(eth_acc._key_obj).to_hex(),
        privateKey = eth_acc.privateKey.hex()
    )

    return account


def account_public_info(account_name: str) -> Tuple[str, str]:
    """Retrieves account public key and address.
    """

    # Check account_name and password
    if len(account_name) == 0:
        return None, None

    db = get_wallet_db()

    acc = db.execute(
        'SELECT * FROM testaccount WHERE name = ?', (account_name,)
    ).fetchone()

    if acc is None:
        return None, None

    return acc["address"], acc["publickey"]


def account(account_name: str, password: str) -> LocalAccount:
    """Retrieves account data from the wallet.
    """

    # Check account_name and password
    if len(account_name) == 0 or len(password) == 0:
        return None

    db = get_wallet_db()

    acc = db.execute(
        'SELECT * FROM testaccount WHERE name = ?', (account_name,)
    ).fetchone()

    if acc is None:
        return None

    # Attemp to decrypt with the provided password
    pk = Account.decrypt(acc["privatekey"], password)
    eth_acc = Account.from_key(pk)

    return eth_acc


def new_account(account_name: str, password: str, overwrite: bool = False) -> LocalAccount:
    """Creates a wallet account. This is essentially a private/public key pair.
    This is NOT an identity yet in blockchain.
    If overwrite is True, a new wallet account is created replacing the old one.
    """
    eth_acc: LocalAccount

    db = get_wallet_db()

    # If not overwrite and account already exists, just return that account
    if overwrite == False:
        eth_acc = account(account_name, password)
        if eth_acc is not None:
            print(f"Account {account_name} exists, reusing it.")
            return eth_acc

    # Generate the private key using Ethereum methods
    eth_acc = Account.create()

    # Get the address (as type str)
    address = eth_acc.address

    # Get the public key (as type eth_keys.datatypes.PublicKey)
    publicKey = eth_acc._key_obj.public_key

    # Encrypt the private key and prepare for saving it
    key_encrypted = eth_acc.encrypt(password)
    key_encrypted = json.dumps(key_encrypted)

    db.execute(
        'REPLACE INTO testaccount (name, address, publickey, privatekey) VALUES (?, ?, ?, ?)',
        (account_name, address, publicKey.to_hex(), key_encrypted)
    )
    # Commit database
    db.commit()

    # Return account data to caller
    return eth_acc


# FINAL: called from Menu

def create_account(account_name, password, overwrite=False):
    """Creates a wallet account. This is essentially a private/public key pair.
    This is NOT an identity yet in Red T.
    """

    db = get_wallet_db()

    # If not overwrite and account already exists, just return that account
    if overwrite == False:
        acc = get_account(account_name, password)
        if acc is not None:
            return acc

    # Generate the private key using Ethereum methods
    acc = Account.create(extra_entropy="Alastria is the first Public-Permissioned Blockchain Network")
    address = acc.address
    publicKey = PublicKey.from_private(acc._key_obj).to_hex()

    # Encrypt the private key and prepare for saving it
    key_encrypted = acc.encrypt(password)
    key_encrypted = json.dumps(key_encrypted)

    db.execute(
        'REPLACE INTO testaccount (name, address, publickey, privatekey) VALUES (?, ?, ?, ?)',
        (account_name, address, publicKey, key_encrypted)
    )
    # Commit database
    db.commit()

    # Return account to caller
    return acc

def m_create_account(account_name, password, overwrite=False):
    """Creates a wallet account. This is essentially a private/public key pair.
    This is NOT an identity yet in Red T.

    --- Definitions ---
    {"name": "account_name", "prompt": "Alias to assign to account", "default": "Myaccount"}
    {"name": "password", "prompt": "Password to encrypt private key", "default": "Mypassword"}
    {"name": "overwrite", "type": "bool", "prompt": "Overwrite if account exists?", "default": False}
    """

    # If not overwrite and account already exists, just return that account
    if overwrite == False:
        acc = get_address(account_name)
        if acc is not None:
            print(f"Account {account_name} already exists and can not overwrite. Exiting.")
            return acc

    acc = create_account(account_name, password, overwrite)
    if acc is None:
        return

    print(f"Account {account_name} created.")


def get_address(account_name, password=""):
    """Gets the address and public key of the account.

    --- Definitions ---
    {"name": "account_name", "prompt": "Alias of account", "default": "Myaccount"}
    """


    db = get_wallet_db()

    account = db.execute(
        'SELECT * FROM testaccount WHERE name = ?', (account_name,)
    ).fetchone()

    if account is None:
        return None

    # Attemp to decrypt with the provided password
    if len(password) > 0:
        pk = Account.decrypt(account["privatekey"], password).hex()
        return {"address": account["address"], "publicKey": account["publickey"], "privateKey": pk}
    else:
        return {"address": account["address"], "publicKey": account["publickey"]}


def create_JWK():
    """Create a private key and return it formatted as JWK
    """

    # Generate the private key using Ethereum methods
    acc = Account.create(extra_entropy="Alastria is the first Public-Permissioned Blockchain Network")

    # Get the public key
    publicKey = PublicKey.from_private(acc._key_obj)

    # The public key is 64 bytes composed of the x and y curve coordinates
    # x and y are each 32 bytes long
    # We convert x and y to hex, so the dictionary can be converted to JSON
    x = publicKey[:32]
    y = publicKey[32:]

    # Create the Json Web Key (JWK) representation, as specified by W3C DID Document format
    key_JWK = JWK(
        kty = "EC",
        crv = "secp256k1",
        d = base64url_encode(acc.privateKey),
        x = base64url_encode(x),
        y = base64url_encode(y)
    )

    return key_JWK


def m_key_JWK(account_name, password):
    """Gets the Private key in JWK format.

    --- Definitions ---
    {"name": "account_name", "prompt": "Account name", "default": "did:elsi:VATES-A87471264"}
    {"name": "password", "prompt": "Password to decrypt private key", "default": "ThePassword"}
    """

    key = key_JWK(account_name, password)

    print(json.dumps(key.export(private_key=True, as_dict=True), ensure_ascii=False, indent=3))

def key_JWK(account_name, password):
    """Gets the Private key in JWK format.

    --- Definitions ---
    {"name": "account_name", "prompt": "Account name", "default": "did:elsi:VATES-A87471264"}
    {"name": "password", "prompt": "Password to decrypt private key", "default": "Mypassword"}
    """

    # The password is required, to be able to get the private key from the database
    if password is None:
        return None

    db = get_wallet_db()

    account = db.execute(
        'SELECT * FROM testaccount WHERE name = ?', (account_name,)
    ).fetchone()

    # Check if account_name was in the database
    if account is None:
        return None

    # Attempt to decrypt the private key with the password and derive the public key
    private_key = Account.decrypt(account["privatekey"], password)
    acc = Account.from_key(private_key)
    publicKey = PublicKey.from_private(acc._key_obj)

    # The public key is 64 bytes composed of the x and y curve coordinates
    # x and y are each 32 bytes long
    # We convert x and y to hex, so the dictionary can be converted to JSON
    x = publicKey[:32]
    y = publicKey[32:]

    # Create the Json Web Key (JWK) representation, as specified by W3C DID Document format
    key_JWK = JWK(
        kty = "EC",
        crv = "secp256k1",
        d = base64url_encode(acc.privateKey),
        x = base64url_encode(x),
        y = base64url_encode(y)
    )

    return key_JWK


def get_account(account_name, password):
    """Displays account data from the wallet.

    --- Definitions ---
    {"name": "account_name", "prompt": "Alias of account", "default": "Myaccount"}
    {"name": "password", "prompt": "Password to decrypt private key", "default": "Mypassword"}
    """

    db = get_wallet_db()

    account = db.execute(
        'SELECT * FROM testaccount WHERE name = ?', (account_name,)
    ).fetchone()

    if account is None:
        return None

    private_key = Account.decrypt(account["privatekey"], password)
    acc = Account.from_key(private_key)

    return acc


def m_get_address(account_name, password):
    """Displays account data from the wallet.

    --- Definitions ---
    {"name": "account_name", "prompt": "Alias of account", "default": "Myaccount"}
    {"name": "password", "prompt": "[Optional]Password of account", "default": ""}
    """

    info = get_address(account_name, password)

    if info is None:
        print(f"Account {account_name} does not exist.")
        return

    print(f"Address: {info['address']}")
    print(f"Public key: {info['publicKey']}")
    if "privateKey" in info:
        print(f"Private key: {info['privateKey']}")

    