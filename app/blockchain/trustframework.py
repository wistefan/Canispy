#!/usr/bin/python3
import xml.etree.ElementTree as ET
import urllib
import click
import os
import inspect
import ast
import subprocess as sp
import requests
import logging
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_keys.datatypes import PrivateKey, PublicKey
import json
import sqlite3
from pprint import pprint
from hexbytes import HexBytes
from typing_extensions import Annotated

from jwcrypto import jwt, jwk, jws
from jwcrypto.common import base64url_decode, base64url_encode


# For the data models
from typing import Any, Dict, Tuple, Optional, cast
from pydantic import BaseModel, BaseSettings, ValidationError

from blockchain import redt as b
from blockchain import wallet

from ens.utils import label_to_hash, raw_name_to_hash

try:
    from devtools import debug
except ImportError:
    def debug(*arg):
        pass


# The settings for the system
from settings import settings

# Initialize some global variables
ENS = None
PublicResolver = None
ens = None
resolver = None

# Initialize logging
log = logging.getLogger(__name__)


####################################################
####################################################
# START: DIDDocument management

class DIDDocument_1(BaseModel):
    pass


# The class representing a DIDDocument for a public entity (legal person)
class DIDDocument:

    def __init__(self, DID: str = None, node_name: str = None, label: str = None, address: str = None, publicKey: bytes = None, manager_account=None):

        self.label = label
        self.node_name = node_name
        self.domain_name = label + "." + node_name
        self.address = address
        self.publicKey = publicKey
        self.manager_account = manager_account

        self.anchors = [
            {
                "id": "redt.alastria",
                "resolution": "UniversalResolver",
                "domain": self.domain_name,
                "ethereumAddress": self.address
            }
        ]

        self.doc = {
            "@context": ["https://www.w3.org/ns/did/v1", "https://w3id.org/security/v1"],
            "id": DID,
            "verificationMethod": [],
            "service": [],
            "anchors": self.anchors,
            "created": "",
            "updated": ""
        }
        self.addPublicKey("key-verification",
                          "JwsVerificationKey2020", publicKey)
        self.setCreated()

    def __str__(self):
        return json.dumps(self.doc, ensure_ascii=False, indent=3)

    @classmethod
    def from_object(self, didDoc: Any):
        self.doc = didDoc
    
    def to_dict(self):
        return self.doc

    def setDID(self, DID):
        self.doc["id"] = DID
        self.setUpdated()

    def DID(self):
        return self.doc["id"]

    def addService(self, service: dict):

        self.doc["service"].append(service)
        self.setUpdated()

    def addPublicKey(self, kid: str, key_type: str, publicKey: bytes):

        # TODO: Use the public key thumbprint for kis (RFC 7638)

        # The public key is 64 bytes composed of the x and y curve coordinates
        # x and y are each 32 bytes long
        # We convert x and y to hex, so the dictionary can be converted to JSON
        x = publicKey[:32]
        y = publicKey[32:]

        # Create the Json Web Key (JWK) representation, as specified by W3C DID Document format
        publicKey_JWK = {
            "id": self.doc["id"]+"#"+kid,
            "type": key_type,
            "controller": self.doc["id"],
            "publicKeyJwk": {
                "kid": kid,
                "kty": "EC",
                "crv": "secp256k1",
                "x": base64url_encode(x),
                "y": base64url_encode(y)
            }
        }

        self.doc["verificationMethod"].append(publicKey_JWK)
        self.setUpdated()

    def addRefPublicKey(self, reference):
        did = self.doc["id"]
        self.doc["publicKey"].append(did+reference)
        self.setUpdated()

    def setCreated(self):
        import datetime as dat
        now = dat.datetime.now(dat.timezone.utc)
        formatted_now = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.doc["created"] = formatted_now
        self.doc["updated"] = formatted_now

    def setUpdated(self):
        import datetime as dat
        now = dat.datetime.now(dat.timezone.utc)
        formatted_now = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.doc["updated"] = formatted_now

    # Create the Identity associated to the DIDDocument
    def createIdentity(self, ens, resolver):

        # Set the DID and DIDDocument
        print(json.dumps(self.doc, ensure_ascii=False, indent=3))
        success, tx_receipt, tx_hash = resolver.setAlaDIDPublicEntity(
            node_name=self.node_name,
            label=self.label,
            DID=self.DID(),
            name=self.domain_name,
            DIDDocument=json.dumps(self.doc, ensure_ascii=False, indent=3),
            active=True,
            new_owner_address=self.address,
            caller_key=self.manager_account.key
        )
        return success, tx_receipt, tx_hash

# END: DIDDocument management
####################################################
####################################################


####################################################
####################################################
# START: ENS
class ENS_class:

    def __init__(self):

        self.initialized = True

    def setRootAccount(self, root_account):
        self.root_account = root_account

    def resolver(self, node_name="root"):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        Resolver_address = ENS.functions.resolver(node_hash).call()
        return Resolver_address

    def owner(self, node_name="root"):
        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        owner = ENS.functions.owner(node_hash).call()
        return owner

    def setSubnodeOwner(self, node_name="root", label=None, new_owner_address=None, current_owner_key=None):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        label_hash = label_to_hash(label)

        contract_fun = ENS.functions.setSubnodeOwner(
            node_hash,
            label_hash,
            new_owner_address)
        success, tx_receipt, tx_hash = b.send_signed_tx(
            contract_fun, current_owner_key)
        return success, tx_receipt, tx_hash

    def setApprovalForAll(self, operator_address, approved, current_owner_key):

        contract_fun = ENS.functions.setApprovalForAll(
            operator_address,
            approved)
        success, tx_receipt, tx_hash = b.send_signed_tx(
            contract_fun, current_owner_key)
        return success, tx_receipt, tx_hash

    def setResolver(self, node_name="root", resolver_address=None, current_owner_key=None):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        contract_fun = ENS.functions.setResolver(
            node_hash,
            resolver_address)
        success, tx_receipt, tx_hash = b.send_signed_tx(
            contract_fun, current_owner_key)
        return success, tx_receipt, tx_hash

    def numberSubnodes(self, node_name="root"):
        node_hash = raw_name_to_hash(node_name)
        num = ENS.functions.numberSubnodes(node_hash).call()
        return num

    def subnode(self, node_name="root", index=0):
        node_hash = raw_name_to_hash(node_name)
        subnode = ENS.functions.subnode(node_hash, int(index)).call()
        return subnode

# END: ENS
####################################################
####################################################

####################################################
####################################################
# START: PUBLIC RESOLVER
class PublicResolver_class:

    def __init__(self):
        pass

    def address(self):
        return PublicResolver.address

    def setName(self, node_name="root", name_to_resolve="root", current_owner_key=None):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        contract_fun = PublicResolver.functions.setName(
            node_hash,
            name_to_resolve)
        success, tx_receipt, tx_hash = b.send_signed_tx(
            contract_fun, current_owner_key)
        return success, tx_receipt, tx_hash

    def name(self, node_name="root", node_hash=None):

        if node_hash is None:
            if node_name == "root":
                node_hash = b.to_32byte_hex(0)
            else:
                node_hash = raw_name_to_hash(node_name)

        name = PublicResolver.functions.name(node_hash).call()

        return name

    def nameFromHash(self, node_hash):

        name = PublicResolver.functions.name(node_hash).call()

        return name

    def setAlaTSP(self, node_name, label, URI, org, active, current_owner_key=None):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        label_hash = label_to_hash(label)

        contract_fun = PublicResolver.functions.setAlaTSP(
            node_hash,
            label_hash,
            URI,
            org,
            active)
        success, tx_receipt, tx_hash = b.send_signed_tx(
            contract_fun, current_owner_key)
        return success, tx_receipt, tx_hash

    def AlaTSP(self, node_name="root", node_hash=None):

        if node_hash is None:
            if node_name == "root":
                node_hash = b.to_32byte_hex(0)
            else:
                node_hash = raw_name_to_hash(node_name)

        URI, org, active = PublicResolver.functions.AlaTSP(node_hash).call()

        return URI, org, active

    def AlaTSPNumberServices(self, node_name="root", node_hash=None):

        if node_hash is None:
            if node_name == "root":
                node_hash = b.to_32byte_hex(0)
            else:
                node_hash = raw_name_to_hash(node_name)

        numServices = PublicResolver.functions.AlaTSPNumberServices(
            node_hash).call()

        return numServices

    def AlaTSPService(self, node_name="root", node_hash=None, index=0):

        if node_hash is None:
            if node_name == "root":
                node_hash = b.to_32byte_hex(0)
            else:
                node_hash = raw_name_to_hash(node_name)

        X509SKI, serviceName, X509Certificate, active = PublicResolver.functions.AlaTSPService(
            node_hash, index).call()

        return X509SKI, serviceName, X509Certificate, active

    def addAlaTSPService(self, node_name, label, X509SKI, serviceName, X509Certificate, active, current_owner_key=None):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        label_hash = label_to_hash(label)

        contract_fun = PublicResolver.functions.addAlaTSPService(
            node_hash,
            label_hash,
            X509SKI,
            serviceName,
            X509Certificate,
            active)
        success, tx_receipt, tx_hash = b.send_signed_tx(
            contract_fun, current_owner_key)
        return success, tx_receipt, tx_hash

    def hash(self, text_to_hash):
        return(b.Web3.keccak(text=text_to_hash))

    def setAlaDIDPublicEntity(self, node_name, label, DID, name, DIDDocument, active, new_owner_address, caller_key):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        label_hash = label_to_hash(label)

        # Calculate the hash of the DID
        DIDHash = b.Web3.keccak(text=DID)

        success, tx_receipt, tx_hash = b.send_signed_tx(
            PublicResolver.functions.setAlaDIDPublicEntity(
                node_hash,
                label_hash,
                DIDHash,
                name,
                DIDDocument,
                active,
                new_owner_address,
            ),
            caller_key
        )

        return success, tx_receipt, tx_hash

    def AlaDIDPublicEntity(self, node_name="root", node_hash=None):

        if node_hash is None:
            if node_name == "root":
                node_hash = b.to_32byte_hex(0)
            else:
                node_hash = raw_name_to_hash(node_name)

        DIDHash, name, DIDDocument, active = PublicResolver.functions.AlaDIDPublicEntity(
            node_hash).call()

        if DIDDocument == "":
            return None, None, None, None

        # Verify integrity: the DIDHash should equal the hash of the DID inside the DIDDocument
        diddoc = json.loads(DIDDocument)
        DID = diddoc["id"]
        did_hash = b.Web3.keccak(text=DID)
        if did_hash == DIDHash:
            return DID, name, DIDDocument, active
        else:
            return None, None, None, None

    def resolveDID(self, _DID: str = None, _DIDHash: HexBytes = None) -> Tuple[str, str, Dict, bool]:

        if _DID is not None:

            # Check that the DID is a string starting with "did:" and that it has some more characters (we accept ANY DID)
            if (not _DID.startswith("did:")) or (len(_DID) <= 4):
                return None, None, None, False

            # Calculate the hash of the DID
            _DIDHash = b.Web3.keccak(text=_DID)

        # Get the node_hash associated to the DID. If the DID is wrong, we get the nil node_hash: bytes32(0)
        node_hash = PublicResolver.functions.nodeFromDID(_DIDHash).call()
        print(f"Node hash for DID {_DID}: {node_hash}")

        # Get the Entity Data associated to the node.
        DID, name, didDoc, active = self.AlaDIDPublicEntity(
            node_hash=node_hash)

        if didDoc is None:
            return None, None, None, False

        # Convert didDoc to python object
        didDoc = json.loads(didDoc)

        return DID, name, didDoc, active

    def setAlaDIDDocument(self, _DID, DIDDocument, caller_key):

        # Check that the DID is a string starting with "did:" and that it has some more characters (we accept ANY DID)
        if (not _DID.startswith("did:")) or (len(_DID) <= 4):
            return None, None, None, False

        # Calculate the hash of the DID
        _DIDHash = b.Web3.keccak(text=_DID)

        success, tx_receipt, tx_hash = b.send_signed_tx(
            PublicResolver.functions.setAlaDIDDocument(
                _DIDHash,
                DIDDocument
            ),
            caller_key
        )

        return success, tx_receipt, tx_hash

    def setCredential(self, node_name="root",
                      key=None,
                      credentialHash=None,
                      participants=[],
                      caller_key=None):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        participantsHash = []
        for i in range(5):
            if i < len(participants):
                participantsHash.append(self.hash(participants[i]))
            else:
                participantsHash.append(bytes(32))

        success, tx_receipt, tx_hash = b.send_signed_tx(
            PublicResolver.functions.setCredential(
                node_hash,
                key,
                credentialHash,
                participantsHash[0],
                participantsHash[1],
                participantsHash[2],
                participantsHash[3],
                participantsHash[4],
            ),
            caller_key
        )

        return success, tx_receipt, tx_hash

    def confirmCredential(self, node_name=None, key=None, participantDID=None, caller_key=None):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        participantHash = self.hash(participantDID)

        success, tx_receipt, tx_hash = b.send_signed_tx(
            PublicResolver.functions.confirmCredential(
                node_hash,
                key,
                participantHash
            ),
            caller_key
        )

        return success, tx_receipt, tx_hash

    def credential(self, node_name=None, key=None):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        credentialHash, numParticipants = PublicResolver.functions.credential(
            node_hash, key).call()
        return credentialHash, numParticipants

    def credentialParticipant(self, node_name=None, key=None, index=0):

        if node_name == "root":
            node_hash = b.to_32byte_hex(0)
        else:
            node_hash = raw_name_to_hash(node_name)

        DIDhash, signed = PublicResolver.functions.credentialParticipant(
            node_hash, key, index).call()
        return DIDhash, signed


# END: PUBLIC RESOLVER
####################################################
####################################################


####################################################
####################################################
# START: Public Credential
class PublicCredential:

    def __init__(self, node_name=None, key=None, credentialHash=None, participantsDID=[], manager_key=None):

        self.node_name = node_name
        self.key = key
        self.credentialHash = credentialHash
        self.manager_key = manager_key
        self.participants = participantsDID

    def addParticipant(self, DIDHash):
        self.participants.append(DIDHash)

    def createCredential(self, ens, resolver):

        success, _, _ = resolver.setCredential(
            node_name=self.node_name,
            key=self.key,
            credentialHash=self.credentialHash,
            participants=self.participants,
            caller_key=self.manager_key
        )

    def confirmCredential(self, node_name=None, key=None, participantDID=None, caller_key=None):

        success, tx_receipt, tx_hash = resolver.confirmCredential(
            node_name, key, participantDID, caller_key
        )


# END: Public Credential
####################################################
####################################################


#################################################################################
#################################################################################
# Commands called from the MENU
#################################################################################
#################################################################################

def m_dump_tf():
    """Dump the Trust Framework

    --- Definitions ---
    """

    # Info about ENS and Resolver Smart Contracts
    #print(f"ENS address: {ens.address()}")
    print(f"ENS address (contract address): {ENS.address}")
    print(f"Resolver address (contract address): {resolver.address()}")
    print(f"Resolver address from ENS(root): {ens.resolver('root')}")
    print("\n")

    print(f"Owner of ROOT record: {ens.owner('root')}")
    ROOT_address, ROOT_key = wallet.account_from_name("ROOT", "ThePassword")
    print(f"ROOT address from wallet: {ROOT_address}")

    n_subnodes = ens.numberSubnodes(0)
    print(f"Number of subnodes of root: {n_subnodes}")
    for i in range(n_subnodes):
        hash = ens.subnode(index=i).hex()
        print(f"   Subnode hash {i}: {ens.subnode(i).hex()}")
        name = resolver.name(node_hash=hash)
        print(f"   Name: {name}")
        resolver_address = ENS.functions.resolver(hash).call()
        print(f"   Resolver: {resolver_address}")
        ala_address = ens.resolver(name)
        print(f"   Resolver by name: {ala_address}")
        owner = owner = ENS.functions.owner(hash).call()
        print(f"   Owner: {owner}")
        ROOT_address, ROOT_key = wallet.account_from_name("Alastria", "ThePassword")
        print(f"   Address from wallet: {ROOT_address}")

    n_subnodes = ens.numberSubnodes("ala")
    print(f"Number of subnodes of {name}: {n_subnodes}")
    for i in range(n_subnodes):
        hash = ens.subnode(node_name="ala", index=i).hex()
        print(f"   Subnode hash {i}: {hash}")
        name = resolver.name(node_hash=hash)
        print(f"   Name: {name}")
        resolver_address = ENS.functions.resolver(hash).call()
        print(f"   Resolver: {resolver_address}")
        ala_address = ens.resolver(name)
        print(f"   Resolver by name: {ala_address}")
        owner = owner = ENS.functions.owner(hash).call()
        print(f"   Owner: {owner}")




def m_create_test_identities():
    """Create test AlastriaID identities in the Trust Framework hierarchy."""

    # Get the ROOT account (it was created in the deployment of the Smart Contracts)
    ROOT_address, ROOT_key = wallet.account_from_name("ROOT", "ThePassword")

    # Create the Alastria account for node "ala"
    print(f"\n==> Creating the Alastria account")
    Alastria_account = wallet.new_account(
        "Alastria", "ThePassword")
    alakey = Alastria_account.key
    print(f"Alastria key: {alakey}")

    print(f"Done")

    # Set the subnode "ala"
    print(f"\n==> Creating the ala subnode in the Trust Framework")
    success, _, _ = ens.setSubnodeOwner(
        node_name="root",
        label="ala",
        new_owner_address=Alastria_account.address,
        current_owner_key=ROOT_key
    )
    print(f"ala subnode created")

    # Assign the name for reverse resolution
    resolver.setName("ala", "ala", Alastria_account.key)

    # And assign approval to the PublicResolver contract so it can call ENS methods on behalf of Alastria
    print(f"Resolver address for ROOT: {resolver.address()}")
    ens.setApprovalForAll(resolver.address(), True, Alastria_account.key)

    ################################
    # Heathrow airport
    print(f"\n==> Creating the Heathrow identity")

    DID = "did:elsi:VATGB-927365404"
    domain_name = "heathrow.ala"
    website = "www.heathrow.com"
    commercial_name = "Heathrow Airport Limited"

    error, didDoc = create_identity(DID, domain_name, website, commercial_name, "Alastria", "ThePassword", False)
    if didDoc is not None:
        pprint(didDoc)

    ################################
    # AENA
    print(f"\n==> Creating the AENA identity")

    DID = "did:elsi:VATES-A86212420"
    domain_name = "aena.ala"
    website = "www.aena.es"
    commercial_name = "Aena"

    error, didDoc = create_identity(DID, domain_name, website, commercial_name, "Alastria", "ThePassword", False)
    if didDoc is not None:
        pprint(didDoc)

    ################################
    # Lanzarote airport
    # The airport belongs to AENA and does not have independent entity (shares the same VAT, for example)
    # In production, the node should be created by AENA, as a subnode controlled by them.
    # In this PoC, the node is created automatically to facilitate the tests
    print(f"\n==> Creating the César Manrique airport identity")

    DID = "did:elsi:VATES-A86212420-1"
    domain_name = "ace.ala"
    website = "www.aena.es/es/aeropuerto-lanzarote"
    commercial_name = "Aeropuerto de Lanzarote-Cesar Manrique"

    error, didDoc = create_identity(DID, domain_name, website, commercial_name, "Alastria", "ThePassword", False)
    if didDoc is not None:
        pprint(didDoc)

    ################################
    # Metrovacesa
    print(f"\n==> Creating the Metrovacesa identity")

    DID = "did:elsi:VATES-A87471264"
    domain_name = "metrovacesa.ala"
    website = "metrovacesa.com"
    commercial_name = "Metrovacesa"

    error, didDoc = create_identity(DID, domain_name, website, commercial_name, "Alastria", "ThePassword", False)
    if didDoc is not None:
        pprint(didDoc)

    ################################
    # IN2
    print(f"\n==> Creating the IN2 identity")

    DID = "did:elsi:VATES-B60645900"
    domain_name = "in2.ala"
    website = "www.in2.es"
    commercial_name = "IN2 Innovating 2gether"

    error, didDoc = create_identity(DID, domain_name, website, commercial_name, "Alastria", "ThePassword", False)
    if didDoc is not None:
        pprint(didDoc)

    ################################
    # Perfect Health
    print(f"\n==> Creating the Perfect Health identity")

    DID = "did:elsi:VATES-X12345678X"
    domain_name = "perfecthealth.ala"
    website = "www.perfecthealth.org"
    commercial_name = "Perfect Health plc"

    error, didDoc = create_identity(DID, domain_name, website, commercial_name, "Alastria", "ThePassword", False)
    if didDoc is not None:
        pprint(didDoc)

    ################################
    # BME
    print(f"\n==> Creating the BME identity")

    DID = "did:elsi:VATES-A83246314"
    domain_name = "bme.ala"
    website = "www.bolsasymercados.es"
    commercial_name = "Bolsas y Mercados Españoles"

    error, didDoc = create_identity(DID, domain_name, website, commercial_name, "Alastria", "ThePassword", False)
    if didDoc is not None:
        pprint(didDoc)



class PublickeyJWK(BaseModel):
    kty: str
    crv: str
    x: str
    y:str

class PrivatekeyJWK(PublickeyJWK):
    d: str


def create_identity_subnode(
        did: str,
        domain_name: str,
        website: str,
        commercial_name: str,
        new_privatekey: PrivatekeyJWK,
        parent_privatekey: PrivatekeyJWK,        
    ) -> Tuple[str, DIDDocument]:
    """Create a new identity in the Trust Framework, as a subnode depending on a parent node.

    The data needed is:
    - did: the DID of the new entity, which has to be created before.
    - domain_name: The full domain name for the new entity. The new subdomain has to depend from an existing domain
    - website: The URL of the website of the new entity
    - commercial_name: The name of the new entity, as it appears in official records
    - new_privatekey: The private key of the new entity, in JWK format.
    - parent_privatekey: The private key of the parent domain, in JWK format

    The call is intended to be called by the entity owning the parent node. After the new identity is created,
    the subnode ownership is assigned to the new entity (that is, the new node can be controlled by the new_privatekey)
    """

    # Check that node has at least two components: subnode.parent
    s = domain_name.partition(".")
    if len(s[1]) == 0:
        return "Domain name has only one component", None

    this_node = s[0]
    parent_node = s[2]

    # Obtain subnode's private and public key and Ethereum address
    subnode_account = Account.from_key(base64url_decode(new_privatekey.d))
    subnode_publicKey = base64url_decode(new_privatekey.x) + base64url_decode(new_privatekey.y)
    pb = PublicKey(subnode_publicKey)
    subnode_address = pb.to_checksum_address()

    # The caller account from its private key
    Manager_account = Account.from_key(base64url_decode(parent_privatekey.d))

    # Initialize the DIDDocument
    didDoc = DIDDocument(
        DID=did,
        node_name=parent_node,
        label=this_node,
        address=subnode_address,
        publicKey=subnode_publicKey,
        manager_account=Manager_account
    )

    # Add the entity info
    service = {
        "id": did + "#info",
        "type": "EntityCommercialInfo",
        "serviceEndpoint": website,
        "name": commercial_name
    }
    didDoc.addService(service)

    # Add the Secure Messaging Server info
    service = {
        "id": did + "#sms",
        "type": "SecureMessagingService",
        "serviceEndpoint": "https://safeisland.hesusruiz.org/api"
    }
    didDoc.addService(service)

    # Store the info in the blockchain trust framework
    success, tx_receipt, tx_hash = didDoc.createIdentity(ens, resolver)
    if not success:
        return "Failed to create identity in blockchain", None

    success, tx_receipt, tx_hash = ens.setApprovalForAll(resolver.address(), True, subnode_account.key)
    if not success:
        return "Failed in setApprovalForAll", None

    return None, didDoc


def create_identity(did: str, domain_name: str, website: str, commercial_name: str, parent_node_account: str, password: str, overwrite: bool=False):

    # Check that node has at least two components
    s = domain_name.partition(".")
    if len(s[1]) == 0:
        return "Domain name has only one component", None

    this_node = s[0]
    parent_node = s[2]

    # The account name will be the unique domain name
    account_name = did

    # Create an external account and save the address and private key.
    # In reality, this should be done by the owner of the identity, and provide only the public key/address
    account = wallet.create_account(account_name, password, overwrite)
    publicKey = PublicKey.from_private(account._key_obj)

    # We assume that the manager account is Alastria, and the password is the one used at creation time
    Manager_account = wallet.get_account(parent_node_account, "ThePassword")
    if Manager_account is None:
        return "Parent node account does not exist", None

    # Initialize the DIDDocument
    didDoc = DIDDocument(
        DID=did,
        node_name=parent_node,
        label=this_node,
        address=account.address,
        publicKey=publicKey,
        manager_account=Manager_account
    )

    # Add the entity info
    service = {
        "id": did + "#info",
        "type": "EntityCommercialInfo",
        "serviceEndpoint": website,
        "name": commercial_name
    }
    didDoc.addService(service)

    # Add the Secure Messaging Server info
    service = {
        "id": did + "#sms",
        "type": "SecureMessagingService",
        "serviceEndpoint": "https://safeisland.hesusruiz.org/api"
    }
    didDoc.addService(service)

    # Store the info in the blockchain trust framework
    success, tx_receipt, tx_hash = didDoc.createIdentity(ens, resolver)
    if not success:
        return "Failed to create identity in blockchain", None

    success, tx_receipt, tx_hash = ens.setApprovalForAll(resolver.address(), True, account.key)
    if not success:
        return "Failed in setApprovalForAll", None

    return None, didDoc



def m_create_identity(DID, domain_name, website, commercial_name, parent_node_account, password, overwrite):
    """Create an identity, with a node name in the Trust Framework and associated DID and address.

    --- Definitions ---
    {"name": "DID", "prompt": "ELSI DID of the new identity", "default": "did:elsi:VATES-B60645900"}
    {"name": "domain_name", "prompt": "Domain name for the new identity", "default": "in2.ala"}
    {"name": "website", "prompt": "Website for the new identity", "default": "www.in2.es"}
    {"name": "commercial_name", "prompt": "Commercial name", "default": "IN2 Innovating 2gether"}
    {"name": "parent_node_account", "prompt": "Account that owns the parent node", "default": "Alastria"}
    {"name": "password", "prompt": "Password to encrypt private key", "default": "ThePassword"}
    {"name": "overwrite", "type": "bool", "prompt": "Overwrite key?", "default": False}
    """

    error, didDoc = create_identity(
        DID, domain_name, website, commercial_name, parent_node_account, password, overwrite)
    if error is not None:
        print(error)

    print(f"Created")


def dump_trusted_identities():
    """Returns all Identities in the system depending from the ala node
    """

    node_name = "ala"

    numberSubnodes = ens.numberSubnodes(node_name)
    id_list = []

    # Iterate for each node
    for i in range(numberSubnodes):

        # Get the subnode (in name_hash format)
        subnode_hash = ens.subnode(node_name, i)

        # Get the data for the subnode
        DID, name, DIDDocument, active = resolver.AlaDIDPublicEntity(
            node_hash=subnode_hash)

        identity = {
            "DID": DID,
            "name": name,
            "node_hash": subnode_hash.hex()
        }
        id_list.append(identity)
        
    return id_list

def m_dump_identities(node_name):
    """Displays all Identities in the system.

    --- Definitions ---
    {"name": "node_name", "prompt": "Hierarchical node name", "default": "metrovacesa.deconfianza.ala"}
    """

    numberSubnodes = ens.numberSubnodes(node_name)
    print(f"\n=> Number of subnodes of node {node_name}: {numberSubnodes}")

    # Iterate for each node
    for i in range(numberSubnodes):

        # Get the subnode (in name_hash format)
        subnode_hash = ens.subnode(node_name, i)

        # Get the data for the subnode
        DID, name, DIDDocument, active = resolver.AlaDIDPublicEntity(
            node_hash=subnode_hash)

        print(f"\n    DID: {DID}, Name: {name}")
        print(f"    Node_hash: {subnode_hash.hex()}")


def m_dump_all_identities():
    """Displays all Identities in the system. Assumes they start at the "ala" TLD."""

    m_dump_identities("ala")


def m_create_test_pubcred():
    """Create test Public Credential trust framework."""

    db = get_db()

    # Get the ROOT account (it was created in the deployment of the ENS)
    ROOT_address, ROOT_key = wallet.account_from_name("ROOT", "ThePassword")

    ###############################################
    # Create the Pubcred account for node "pubcred" (address/private key)
    print(f"\n==> Creating the Pubcred account")
    Pubcred_account = wallet.create_and_save_account("Pubcred", "ThePassword")
    print(f"Done")

    # Create subnode "pubcred" and assign ownership to Pubcred address
    print(f"\n==> Creating the pubcred subnode in the Trust Framework")
    success, _, _ = ens.setSubnodeOwner(
        node_name="root",
        label="pubcred",
        new_owner_address=Pubcred_account.address,
        current_owner_key=ROOT_key
    )

    # Authorize the PublicResolver contract to call ENS on behalf of Pubcred
    ens.setApprovalForAll(resolver.address(), True, Pubcred_account.key)

    # Assign the name for easy reverse resolution
    resolver.setName("pubcred", "pubcred", Pubcred_account.key)
    print(f"pubcred subnode created")

    ###################################################################
    # Create the Deconfianza account for node "deconfianza"
    print(f"\n==> Creating the Deconfianza account")
    Deconfianza_account = wallet.create_and_save_account(
        "Deconfianza", "ThePassword")
    print(f"Done")

    # Create subnode "deconfianza.pubcred" and assign ownership to Deconfianza address
    # This is the node at the root of the DECONFIANZA ecosystem
    print(f"\n==> Creating the deconfianza.prubcred subnode in the Trust Framework")
    success, _, _ = ens.setSubnodeOwner(
        node_name="pubcred",
        label="deconfianza",
        new_owner_address=Deconfianza_account.address,
        current_owner_key=Pubcred_account.key
    )

    # Authorize the PublicResolver contract to call ENS on behalf of Deconfianza
    ens.setApprovalForAll(resolver.address(), True, Deconfianza_account.key)

    # Assign the name for reverse resolution
    resolver.setName("deconfianza.pubcred",
                     "deconfianza.pubcred", Deconfianza_account.key)
    print(f"deconfianza.pubcred subnode created")

    ###################################################################
    # Get the Metrovacesa account, that was created as part of the Identity creation
    Metrovacesa_address, Metrovacesa_key = wallet.account_from_name(
        "metrovacesa.ala", "ThePassword")

    # Create subnode "metrovacesa.deconfianza.pubcred" and assign ownership to Metrovacesa
    # Metrovacesa will be able to manage this node and create Public Credentials
    print(f"\n==> Creating the metrovacesa.deconfianza.prubcred subnode in the Trust Framework")
    success, _, _ = ens.setSubnodeOwner(
        node_name="deconfianza.pubcred",
        label="metrovacesa",
        new_owner_address=Metrovacesa_address,
        current_owner_key=Deconfianza_account.key
    )

    # Authorize the PublicResolver contract to call ENS on behalf of Deconfianza
    ens.setApprovalForAll(resolver.address(), True, Metrovacesa_key)

    # Assign the name for reverse resolution
    resolver.setName("metrovacesa.deconfianza.pubcred",
                     "metrovacesa.deconfianza.pubcred", Metrovacesa_key)
    print(f"metrovacesa.deconfianza.pubcred subnode created")

    #####################################
    #####################################
    print(f"\n==> Creating the Public Credential associated to the metrovacesa.deconfianza.prubcred node")
    Metrovacesa_DID = "did:elsi:VATES-A87471264"
    IN2_DID = "did:elsi:VATES-B60645900"
    BME_DID = "did:elsi:VATES-A83246314"

    participants = [
        Metrovacesa_DID,
        IN2_DID,
        BME_DID
    ]

    pubcred = PublicCredential(
        node_name="metrovacesa.deconfianza.pubcred",
        key="Promocion1",
        credentialHash=b"hola",
        participantsDID=participants,
        manager_key=Metrovacesa_key
    )
    # Store the info in the blockchain trust framework
    pubcred.createCredential(ens, resolver)
    print("Created")


def m_credential_create(node_name, credential_hash, participantDID):
    """Creates a credential.

    --- Definitions ---
    {"name": "node_name", "prompt": "Hierarchical node name", "default": "metrovacesa.deconfianza.pubcred"}
    {"name": "credential_hash", "prompt": "Credential hash", "default": "Hola que tal"}
    {"name": "participantDID", "prompt": "Participant DID", "default": "did:elsi:VATES-B60645900"}
    """
    pass


def m_credential_confirm(node_name, key, participantDID, account_name):
    """Creates a credential.

    --- Definitions ---
    {"name": "node_name", "prompt": "Hierarchical node name", "default": "metrovacesa.deconfianza.pubcred"}
    {"name": "key", "prompt": "Unique name of the credential, as a key", "default": "Promocion1"}
    {"name": "participantDID", "prompt": "Participant DID", "default": "did:elsi:VATES-B60645900"}
    {"name": "account_name", "prompt": "Account name", "default": "in2.ala"}
    """
    # Confirm the credential
    acc_address, acc_key = wallet.account_from_name(
        account_name, "ThePassword")
    if acc_address is None:
        print(f"Account {account_name} does not exist")
        return

    print(f"\n==> Confirming the credential by {account_name}")

    try:
        resolver.confirmCredential(
            node_name=node_name,
            key=key,
            participantDID=participantDID,
            caller_key=acc_key
        )
    except ValueError as err:
        print(f"Error: {err}")
    else:
        print("Confirmed!")


def m_credential_display(node_name, key):
    """Displays a credential.

    --- Definitions ---
    {"name": "node_name", "prompt": "Hierarchical node name", "default": "metrovacesa.deconfianza.pubcred"}
    {"name": "key", "prompt": "Unique name of the credential, as a key", "default": "Promocion1"}
    """
    # Confirm the credential

    try:
        credentialHash, numParticipants = resolver.credential(
            node_name=node_name, key=key)
    except ValueError as err:
        print(f"Error: {err}")
        return

    print(f"Credential hash: {credentialHash}")
    print(f"Number of participants: {numParticipants}")

    for i in range(numParticipants):
        DIDHash, signed = resolver.credentialParticipant(
            node_name=node_name, key=key, index=i)
        DID, name, DIDDocument, active = resolver.resolveDID(_DIDHash=DIDHash)

        print(f"\n    DID: {DID}")
        print(f"    Name: {name}")
        print(f"    Signed: {signed}")


def m_get_owner(node_name):
    """Gets the owner of a given node.

    --- Definitions ---
    {"name": "node_name", "prompt": "Hierarchical node name", "default": "metrovacesa.deconfianza.ala"}
    """

    # Initialize the contract classes. These classes only work when the smart contracts are already deployed
#    ens = ENS_class()
#    resolver = PublicResolver_class()

    # Get the owner of the node name
    owner = ens.owner(node_name)
    print(f"Owner address: {owner}")

    # Check if we received the zero address
    if int(owner, base=16) == 0:
        print(f"No owner (or the record is the root record)")
        return

    # Check in the database to see if we have it
    name, pubkey = wallet.account_from_address(owner)
    print(f"Name from the database: {name}")


def m_get_subnode(node_name, index):
    """Gets the subnode at the given index of a specified node.

    --- Definitions ---
    {"name": "node_name", "prompt": "Hierarchical node name", "default": "metrovacesa.deconfianza.ala"}
    {"name": "index", "prompt": "Index of the subnode", "default": "0"}
    """

    # Initialize the contract classes. These classes only work when the smart contracts are already deployed
#    ens = ENS_class()
#    resolver = PublicResolver_class()

    subnode_hash = ens.subnode(node_name, index)

    # Check if we received a cero value (32 bytes will with zeroes)
    if subnode_hash == bytes(32):
        print(f"There are no subnodes")
        return

    # Try to resolve the name from the blockchain
    subnode_name = resolver.name(node_hash=subnode_hash)
    if len(subnode_name) > 0:
        print(
            f"Subnode_hash: {subnode_hash.hex()}, Subnode name: {subnode_name}")
    else:
        print(
            f"Subnode_hash: {subnode_hash.hex()}, could not be resolved to a name.")



def m_get_DIDDocument(DID):
    """Gets the entity data of a given did.

    --- Definitions ---
    {"name": "DID", "prompt": "The DID to resolve", "default": "did:elsi:VATES-A87471264"}
    """

    DID, name, DIDDocument, active = resolver.resolveDID(DID)

    print(f"Name: : {name}")
    print(json.dumps(DIDDocument, ensure_ascii=False, indent=3))


#################################################################################
#################################################################################
# Utilities
#################################################################################
#################################################################################

def connect_blockchain(provider=settings.BLOCKCHAIN_NODE_IP):

    # Connect with the right provider
    b.setup_provider(provider)

    # The path to the contracts deployment artifacts
    ENSRegistry_full_path = os.path.join(settings.CONTRACTS_OUTPUT_DIR, "ENSRegistry")
    PublicResolver_full_path = os.path.join(settings.CONTRACTS_OUTPUT_DIR, "PublicResolver")

    # Bind the ENS and Resolver contracts
    global ENS
    global PublicResolver
    global ens
    global resolver
    ENS = b.bind_contract(ENSRegistry_full_path)
    PublicResolver = b.bind_contract(PublicResolver_full_path)

    # Initialize the high-level contract classes
    ens = ENS_class()
    resolver = PublicResolver_class()

    return ENS, PublicResolver



def get_db():
    db_name = os.path.join(settings.DATABASE_DIR, "pubcred_config.sqlite")
    db = sqlite3.connect(db_name, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db


def m_setName(node_name="root", name_to_resolve="root", current_owner_alias="ROOT"):
    """Assigns the name to the given record.

    --- Definitions ---
    {"name": "node_name", "prompt": "Node name of the owner of the record?", "default": "root"}
    {"name": "name_to_resolve", "prompt": "Name to assign for reverse resolution", "default": "publicresolver"}
    {"name": "current_owner_alias", "prompt": "Alias of the owner of the key", "default": "ROOT"}
    """

    # Get the account info from the alias
    account_address, account_key = wallet.account_from_name(
        current_owner_alias, "ThePassword")

    # Set the name
    resolver.setName(node_name, name_to_resolve, account_key)


def m_getName(node_name="root"):
    """Gets the assigned name of the record.

    --- Definitions ---
    {"name": "node_name", "prompt": "Node name of the owner of the record?", "default": "root"}
    """

    name = resolver.name(node_name=node_name)
    if name == None:
        print("No name assigned")
    else:
        print(f"Name: {name}")

    return name

