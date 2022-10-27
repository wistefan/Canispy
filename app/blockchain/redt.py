import sys
import time
import pprint
import os
import json
from hexbytes.main import HexBytes
import web3
from pathlib import Path

from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3.eth import Eth
from typing import Optional, Tuple

from web3.types import TxReceipt

from devtools import debug as debug_print


# Define the global variable w3, to be used later
w3 = None

##########################################################################
# Auxiliary procedures
##########################################################################

debug = True
#debug = True

# Defaul providers
Ganache = "HTTP://127.0.0.1:7545"
IN2_Red_T_node = "HTTP://15.236.0.91:22000"

# Convert to an Ethereum bytes32 value
def to_32byte_hex(val):
    return Web3.toHex(Web3.toBytes(val).rjust(32, b'\0'))

# Convert to a Hex value
def toHex(val):
    return Web3.toHex(hexstr=val)

# Convert a raw address to a checksum-formatted address
def toChecksumAddress(rawAddress):
    address = Web3.toChecksumAddress(rawAddress)
    return address

def checkTxReceipt(tx_receipt, gas):

    # Check for successful transaction execution
    # The logic is verbose intentionally, to make it explicit an easier to understand
    success = False
    # After Byzantium, the transaction receipt contains a "status" field
    # The transaction succeeded if status == 1
    if "status" in tx_receipt:
        if (tx_receipt.status == 1):
            success = True
    else:
        # Before Byzantium, the transaction receipt did not have a "status" field,
        # so the only way to check for success is to compare gas provided to gas consumed.
        # If both are equal, then the transaction did not execute correctly.
        if gas == tx_receipt.gasUsed:
            success = False
        else:
            success = True

    return success

# Deploy a contract with variable number of arguments in the constructor
def deploy_public_resolver(contractName: str, ens_address: str = None, private_key = None, timeout=20, *args):

    # Get the ABI for the contract.
    # Assume there is a file with the contract name and extension .abi
    fullpath = contractName + ".abi"
    with open(fullpath) as f:
        abi = f.read()

    # Get the bytecode for the contract.
    # Assume there is a file with the conract name and extension .bin
    fullpath = contractName + ".bin"
    with open(fullpath) as f:
        bytecode = f.read()

    # Obtain the contract wrapper, including the ABI and the actual bytecodes
    contractWrapper = w3.eth.contract(
        abi=abi,
        bytecode=bytecode)

    # Submit the transaction that deploys the contract
    # Supply the same arguments that we received
    # tx_hash = contractWrapper.constructor(*args).transact(txparms)

    # Get the deployment transaction, in order to sign and send it
    constructor = contractWrapper.constructor(ens_address)
    
    # Send a signed transaction, with the private key of an external account
    result, tx_receipt, tx_hash = send_signed_tx(
        constructor,
        private_key,
        timeout)

    if result == False:
        return False, tx_receipt, None

    # get the contract address as a checksum address
    address = tx_receipt['contractAddress']
    address = toChecksumAddress(address)

    # Write the deployment address of the contract so it can be called later
    fullpath = contractName + ".addr"
    with open(fullpath, "w") as f:
        f.write(str(address))

    return True, tx_receipt, address




# Deploy a contract with variable number of arguments in the constructor
def deploy_contract(contractName: str, private_key: HexBytes, timeout: int = 20, *args):

    # Get the ABI for the contract.
    # Assume there is a file with the contract name and extension .abi
    fullpath = contractName + ".abi"
    with open(fullpath) as f:
        abi = f.read()

    # Get the bytecode for the contract.
    # Assume there is a file with the conract name and extension .bin
    fullpath = contractName + ".bin"
    with open(fullpath) as f:
        bytecode = f.read()

    # Obtain the contract wrapper, including the ABI and the actual bytecodes
    contractWrapper = w3.eth.contract(
        abi=abi,
        bytecode=bytecode)

    # Submit the transaction that deploys the contract
    # Supply the same arguments that we received
    # tx_hash = contractWrapper.constructor(*args).transact(txparms)

    # Get the deployment transaction, in order to sign and send it
    constructor = contractWrapper.constructor(*args)
    
    # Send a signed transaction, with the private key of an external account
    result, tx_receipt, tx_hash = send_signed_tx(
        constructor,
        private_key,
        timeout)

    if result == False:
        return False, tx_receipt, None

    # get the contract address as a checksum address
    address = tx_receipt['contractAddress']
    address = toChecksumAddress(address)

    # Write the deployment address of the contract so it can be called later
    fullpath = contractName + ".addr"
    with open(fullpath, "w") as f:
        f.write(str(address))

    return True, tx_receipt, address


# Deploy a contract with variable number of arguments in the constructor
def deploy_contract_raw(contractName: str, abi=None, bytecode=None ,private_key: HexBytes = None, timeout: str=20, *args):

    # Obtain the contract wrapper, including the ABI and the actual bytecodes
    contractWrapper = w3.eth.contract(
        abi=abi,
        bytecode=bytecode)

    # Get the deployment transaction, in order to sign and send it
    constructor = contractWrapper.constructor(*args)
    
    # Send a signed transaction, with the private key of an external account
    result, tx_receipt, tx_hash = send_signed_tx(
        constructor,
        private_key,
        timeout)

    if result == False:
        return False, tx_receipt, None

    # get the contract address as a checksum address
    address = tx_receipt['contractAddress']
    address = toChecksumAddress(address)

    # Write the deployment address of the contract so it can be called later
    fullpath = contractName + ".addr"
    with open(fullpath, "w") as f:
        f.write(str(address))

    return True, tx_receipt, address



# Bind a contract definition to a deployment address in the blockchain
# The contractName variable is used to build the filenames for where the ABI and Address
# of the contract are stored
def bind_contract(contractName: str):

    # Get the ABI for the contract. We assume the existence of a file with extension ".abi"
    fullpath = contractName + ".abi"
    with open(fullpath) as f:
        abi = f.read()

    # Get the address of the deployed contract
    # We assume the existence of a file with extension ".addr"
    fullpath = contractName + ".addr"
    with open(fullpath) as f:
        raw_contract_address = f.read()

    # Convert the raw address to a checksum address
    contract_address = Web3.toChecksumAddress(raw_contract_address)

    # Bind the address to the contract interface so we can call its functions
    # We get a wrapper class with all the functions of the Solidity contract
    wrapper = w3.eth.contract(
        address=contract_address,
        abi=abi)

    return wrapper

# Bind a contract definition to a deployment address in the blockchain
# The contractName variable is used to build the filenames for where the ABI
# of the contract is stored
def bind_contract_with_address(contractName, address):

    # Get the ABI for the contract. We assume the existence of a file with extension ".abi"
    fullpath = contractName + ".abi"
    with open(fullpath) as f:
        abi = f.read()

     # Convert the raw address to a checksum address
    contract_address = Web3.toChecksumAddress(address)

    # Bind the address to the contract interface so we can call its functions
    # We get a wrapper class with all the functions of the Solidity contract
    wrapper = w3.eth.contract(
        address=contract_address,
        abi=abi)

    return wrapper

# Create a signed transaction with the private key, send it and wait timeout for the txreceipt
def send_signed_tx(contract_function, private_key: HexBytes = None, timeout: int=20):

    if debug:
        print(f"Entering send_signed_tx with PrivateKey: {private_key}")

    # Obtain the account associated to the private key
    from_account = Account.privateKeyToAccount(private_key)

    # Obtain the transaction count for the account, to build the nonce for the transaction
    nonce = w3.eth.getTransactionCount(from_account.address)
    if debug:
        print(f"Nonce: {nonce}")

    # Define a high value of gas. For the moment this is not important
    gas = 9000000

    # Create a transaction parameter specification with enough gas for executions
    txparms = {
        'gasPrice': 0,
        'gas': gas,
        'nonce': nonce
    }

    # Build the transaction object for the invocation to the provided function
    unsignedTx = contract_function.buildTransaction(txparms)
    if debug:
        print(f"Built the transaction object")
        print(f"Unsingend tx: {unsignedTx}")

    # Sign the transaction with the private key
    # This way we can send the transaction without relying on accounts hosted in any node
    # It will act as sending the transaction from the account associated to the private key
    signedTx = Account.signTransaction(unsignedTx, private_key)
    if debug:
        print(f"SignedTx: {signedTx}")

    # Send the signed transaction
    tx_hash = w3.eth.sendRawTransaction(signedTx.rawTransaction)
    if debug:
        print(f"Transaction sent with hash: {tx_hash}")

    # Wait for the receipt at most "timeout" seconds
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout)
    if debug:
        print(f"Receipt: {tx_receipt}")

    # Check if the transaction executed correctly
    success = checkTxReceipt(tx_receipt, gas)
    if debug:
        print(f"Success: {success}")
    return success, tx_receipt, tx_hash

# To simplify waiting for the transaction receipt
# Returns the success indicator (True or false) and the receipt
def waitForReceipt(tx_hash, timeout=20):

    # Wait for the receipt at most "timeout" seconds
    receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout)

    # Check for successful transaction execution
    return (receipt.status == 1), receipt


# Tell W3 where the node is
def setup_provider(node_ip):

    global w3

    # Create a web3.py instance connecting with an Alastria node
    w3 = Web3(Web3.HTTPProvider(node_ip))

    # Inject the POA compatibility middleware to the innermost layer
    from web3.middleware import geth_poa_middleware
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    # Return the Web3 instance
    return w3


def get_transaction_receipt(tx_hash) -> TxReceipt:
    tx_receipt = w3.eth.get_transaction_receipt(tx_hash)

    # Convert the transaction receipt to a standard python dict
    receipt = json.loads(Web3.toJSON(tx_receipt))

    return receipt