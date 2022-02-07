#!/usr/bin/python3

import os
import inspect
import ast
import logging

import base64
import json
from subprocess import run

from hexbytes import HexBytes
from devtools import debug

import typer

log = logging.getLogger(__name__)

from settings import settings

from blockchain import redt as b
from blockchain import trustframework as tf
from blockchain import wallet, certificates, safeisland, eutl, pubcred
from blockchain import christmas, compile

from utils.menu import Menu, invoke

timestamper_bin = "6080604052336000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555034801561005057600080fd5b50336000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff160217905550610530806100a06000396000f3fe608060405234801561001057600080fd5b5060043610610053576000357c01000000000000000000000000000000000000000000000000000000009004806351488aae14610058578063b97da33b14610074575b600080fd5b610072600480360381019061006d919061039b565b610090565b005b61008e60048036038101906100899190610413565b61016e565b005b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff16146100e857600080fd5b60005b82518110156101695781818151811061010757610106610453565b5b602002602001015183828151811061012257610121610453565b5b60200260200101517fa3865c00e01495fc2b86502cae36a4edb139f748682e7d80725a3d6571a482fa60405160405180910390a38080610161906104b1565b9150506100eb565b505050565b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff16146101c657600080fd5b80827fa3865c00e01495fc2b86502cae36a4edb139f748682e7d80725a3d6571a482fa60405160405180910390a35050565b6000604051905090565b600080fd5b600080fd5b600080fd5b6000601f19601f8301169050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b61025a82610211565b810181811067ffffffffffffffff8211171561027957610278610222565b5b80604052505050565b600061028c6101f8565b90506102988282610251565b919050565b600067ffffffffffffffff8211156102b8576102b7610222565b5b602082029050602081019050919050565b600080fd5b6000819050919050565b6102e1816102ce565b81146102ec57600080fd5b50565b6000813590506102fe816102d8565b92915050565b60006103176103128461029d565b610282565b9050808382526020820190506020840283018581111561033a576103396102c9565b5b835b81811015610363578061034f88826102ef565b84526020840193505060208101905061033c565b5050509392505050565b600082601f8301126103825761038161020c565b5b8135610392848260208601610304565b91505092915050565b600080604083850312156103b2576103b1610202565b5b600083013567ffffffffffffffff8111156103d0576103cf610207565b5b6103dc8582860161036d565b925050602083013567ffffffffffffffff8111156103fd576103fc610207565b5b6104098582860161036d565b9150509250929050565b6000806040838503121561042a57610429610202565b5b6000610438858286016102ef565b9250506020610449858286016102ef565b9150509250929050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052603260045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b60006104bc826102ce565b91507fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8214156104ef576104ee610482565b5b60018201905091905056fea26469706673582212208c0c46ae3e2038f671c0dad478b46df5ced986ab216eecdd0cc6939874e4ef0a64736f6c63430008090033"


gserver = "127.0.0.1:9200"

grcmd = os.path.join(settings.TOLAR_DIR, "grpcurl")

def string_to_b64str(a: str):
    return base64.b64encode(a.encode("ascii")).decode("ascii")

def b64str_to_string(b64str: str):
    a = base64.b64decode(b64str)
    return a.decode("ascii")

def b64str_to_int(b64str: str):
    return int.from_bytes(base64.b64decode(b64str), "big")

def bytes_to_b64str(v):
    enc = base64.b64encode(v)
    return enc.decode("ascii")

def int_to_b64str(v: int):
    b = int(v)
    enc = base64.b64encode(b.to_bytes((b.bit_length() + 7) // 8, "big"))
    return enc.decode("ascii")

def hash(any_hash: str) -> str:
    """Converts b64 and normal hashes to a normal hash"""
    if len(any_hash) == 64:
        # Assume it is a normal hash
        return any_hash
    else:
        # Assume it is a b64 hash
        return b64str_to_string(any_hash)

def hashb64(any_hash: str) -> str:
    """Converts b64 and normal hashes to a b64 hash"""
    if len(any_hash) == 64:
        # Assume it is a normal hash
        return string_to_b64str(any_hash)
    else:
        # Assume it is a b64 hash
        return any_hash

def address(any_address: str) -> str:
    """Converts b64 and normal addresses to a normal address"""
    if len(any_address) == 50:
        # Assume it is a normal address
        return any_address
    else:
        # Assume it is a b64 address
        return b64str_to_string(any_address)

def addressb64(any_address: str) -> str:
    """Converts b64 and normal addresses to a b64 address"""
    if len(any_address) == 50:
        # Assume it is a normal address
        return string_to_b64str(any_address)
    else:
        # Assume it is a b64 address
        return any_address


def list_top_services():
    run([grcmd, "-plaintext", gserver, "list"])    

class Tolar():

    services = {
        # Account services
        "ChangeAddressPassword": "tolar.proto.AccountService.ChangeAddressPassword",
        "ChangePassword": "tolar.proto.AccountService.ChangePassword",
        "Create": "tolar.proto.AccountService.Create",
        "CreateNewAddress": "tolar.proto.AccountService.CreateNewAddress",
        "ExportKeyFile": "tolar.proto.AccountService.ExportKeyFile",
        "ImportKeyFile": "tolar.proto.AccountService.ImportKeyFile",
        "ImportRawPrivateKey": "tolar.proto.AccountService.ImportRawPrivateKey",
        "ListAddresses": "tolar.proto.AccountService.ListAddresses",
        "ListBalancePerAddress": "tolar.proto.AccountService.ListBalancePerAddress",
        "Open": "tolar.proto.AccountService.Open",
        "SendDeployContractTransaction": "tolar.proto.AccountService.SendDeployContractTransaction",
        "SendExecuteFunctionTransaction": "tolar.proto.AccountService.SendExecuteFunctionTransaction",
        "SendFundTransferTransaction": "tolar.proto.AccountService.SendFundTransferTransaction",
        "SendRawTransaction": "tolar.proto.AccountService.SendRawTransaction",
        "VerifyAddress": "tolar.proto.AccountService.VerifyAddress",

        # Blockchain services
        "GetBalance": "tolar.proto.BlockchainService.GetBalance",
        "GetBlockByHash": "tolar.proto.BlockchainService.GetBlockByHash",
        "GetBlockByIndex": "tolar.proto.BlockchainService.GetBlockByIndex",
        "GetBlockCount": "tolar.proto.BlockchainService.GetBlockCount",
        "GetBlockchainInfo": "tolar.proto.BlockchainService.GetBlockchainInfo",
        "GetCompleteBlockByIndex": "tolar.proto.BlockchainService.GetCompleteBlockByIndex",
        "GetGasEstimate": "tolar.proto.BlockchainService.GetGasEstimate",
        "GetLatestBalance": "tolar.proto.BlockchainService.GetLatestBalance",
        "GetLatestBlock": "tolar.proto.BlockchainService.GetLatestBlock",
        "GetNonce": "tolar.proto.BlockchainService.GetNonce",
        "GetPaginatedBlocksByIndexStream": "tolar.proto.BlockchainService.GetPaginatedBlocksByIndexStream",
        "GetTransaction": "tolar.proto.BlockchainService.GetTransaction",
        "GetTransactionList": "tolar.proto.BlockchainService.GetTransactionList",
        "GetTransactionReceipt": "tolar.proto.BlockchainService.GetTransactionReceipt",
        "TryCallTransaction": "tolar.proto.BlockchainService.TryCallTransaction",

        # Transaction services
        "SendSignedTransaction": "tolar.proto.TransactionService.SendSignedTransaction",

    }

    def __init__(self, server) -> None:
        self.server = server

    def set_contract_wrapper(self, wrapper):
        self.contract_wrapper = wrapper

    def _run_cmd(self, cmd):
        p = run(cmd, capture_output=True, text=True)
        return p

    def list(self):
        run([grcmd, "-plaintext", self.server, "list", "tolar.proto.AccountService"])
        print()
        run([grcmd, "-plaintext", self.server, "list", "tolar.proto.BlockchainService"])
        print()
        run([grcmd, "-plaintext", self.server, "list", "tolar.proto.NetworkService"])
        print()
        run([grcmd, "-plaintext", self.server, "list", "tolar.proto.TransactionService"])
        

    def open(self):
        """Open keystore
        """
        p = run([grcmd, "-plaintext", self.server, self.services["Open"]], capture_output=True, text=True)
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")

    def create(self):
        """Create keystore
        """
        p = self._run_cmd([grcmd, "-plaintext", self.server, self.services["Create"]])
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")

    def list_adddresses(self):
        """List addresses
        """
        p = self._run_cmd([grcmd, "-plaintext", self.server, self.services["ListAddresses"]])
        p.check_returncode()
        out = json.loads(p.stdout)
        addresses = out["addresses"]
        for i in range(len(addresses)):
            addresses[i] = address(addresses[i])
        debug(addresses)
        return addresses
            
    def create_new_address(self):
        """Create new address
        """
        p = self._run_cmd([grcmd, "-plaintext", self.server, self.services["CreateNewAddress"]])
        p.check_returncode()
        out = json.loads(p.stdout)
        print(f"Created: {out['address']}")
        return address(out['address'])

    def import_raw_private_key(self, private_key: str):
        """Get Nonce
        
        --- Definitions ---
        {"name": "private_key", "prompt": "Private key", "default": "b69cec59d98f8d73de5d12cf9fd41de1403c5db9e5da55f01ac91746a1cbeb2d"}
        """

        # a = string_to_b64str(address)
        data = {
            "raw_private_key": private_key,
        }
        data = json.dumps(data)

        p = self._run_cmd([grcmd, "-d", data, "-plaintext", self.server, self.services["ImportRawPrivateKey"]])
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")
            return
        out = json.loads(p.stdout)
        print(f"{out}")

    def SendDeployContractTransaction(self, address: str):
        """Deploy Smart Contract
        
        --- Definitions ---
        {"name": "address", "prompt": "Address", "default": "54d0b0bc6cbbd54d0ec605cbf87819763445e70ef24fc85c20"}
        """

        my_address = "54d0b0bc6cbbd54d0ec605cbf87819763445e70ef24fc85c20"
        sender_address = string_to_b64str(my_address)

        amount = int_to_b64str(0)
        gas = int_to_b64str(10000000)
        gas_price = int_to_b64str(1000000000000)
        contract_data = HexBytes.fromhex(timestamper_bin)
        contract_data = bytes_to_b64str(contract_data)
        nonce = int_to_b64str(self.get_nonce(my_address))

        data = {
            "sender_address": sender_address,
            "amount": amount,
            "gas": gas,
            "gas_price": gas_price,
            "data": contract_data,
            "nonce": nonce,
        }
        debug(data)
        data = json.dumps(data)

        p = self._run_cmd([grcmd, "-d", data, "-plaintext", self.server, self.services["SendDeployContractTransaction"]])
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")
            return
        out = json.loads(p.stdout)
        print(f"{out}")


    def TryCallTransaction(self, address: str):
        """Deploy Smart Contract
        
        --- Definitions ---
        {"name": "address", "prompt": "Address", "default": "54d0b0bc6cbbd54d0ec605cbf87819763445e70ef24fc85c20"}
        """

        my_address = "54d0b0bc6cbbd54d0ec605cbf87819763445e70ef24fc85c20"
        sender_address = string_to_b64str(my_address)

        gas = int_to_b64str(210000)
        gas_price = int_to_b64str(1)
        contract_data = string_to_b64str(timestamper_bin)
        nonce = int_to_b64str(self.get_nonce(my_address))

        data = {
            "sender_address": sender_address,
            "gas": gas,
            "gas_price": gas_price,
            "data": contract_data,
            "nonce": nonce,
        }
        debug(data)

        data = json.dumps(data)

        p = self._run_cmd([grcmd, "-d", data, "-plaintext", self.server, self.services["TryCallTransaction"]])
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")
            return
        out = json.loads(p.stdout)
        print(f"{out}")

    def get_transaction_data(self, hash1, hash2):

        # Get the contract wrapper
        contract_fun = self.contract_wrapper.functions.timestamp(hash1, hash2)

        # Create a transaction parameter specification with enough gas for executions
        txparms = {
            'gasPrice': 0,
            'gas': 9000000,
            'nonce': 23
        }

        # Build the transaction object for the invocation to the provided function
        unsignedTx = contract_fun.buildTransaction(txparms)
        return unsignedTx["data"]


    def SendExecuteFunctionTransaction(self,
        transaction_data,
        sender_address: str = "54d0b0bc6cbbd54d0ec605cbf87819763445e70ef24fc85c20",
        receiver_address: str = "54ece245cc634e8fb2ef6ba2d80fac0d8bb25a5979c2340279",
        ) -> dict:
        """SendExecuteFunctionTransaction
        
        --- Definitions ---
        {"name": "sender_address", "prompt": "Sender address", "default": "54d0b0bc6cbbd54d0ec605cbf87819763445e70ef24fc85c20"}
        {"name": "receiver_address", "prompt": "Receiver address", "default": "54ece245cc634e8fb2ef6ba2d80fac0d8bb25a5979c2340279"}
        """

        sender_address_b64 = addressb64(sender_address)
        receiver_address_b64 = addressb64(receiver_address)

        amount = int_to_b64str(0)

        gas = int_to_b64str(10000000)
        gas_price = int_to_b64str(1000000000000)

        contract_data = transaction_data
        contract_data = HexBytes(contract_data)
        contract_data = bytes_to_b64str(contract_data)
        
        nonce = int_to_b64str(self.get_nonce(sender_address))

        data = {
            "sender_address": sender_address_b64,
            "receiver_address": receiver_address_b64,
            "amount": amount,
            "gas": gas,
            "gas_price": gas_price,
            "data": contract_data,
            "nonce": nonce,
        }
        debug(data)
        data = json.dumps(data)

        p = self._run_cmd([grcmd, "-d", data, "-plaintext", self.server, self.services["SendExecuteFunctionTransaction"]])
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")
            return
        out = json.loads(p.stdout)
        out["transactionHash"] = hash(out["transactionHash"])
        print(f"{out}")
        tx_receipt = self.GetTransactionReceipt(out["transactionHash"])
        return tx_receipt

    def GetTransactionReceipt(self, transaction_hash: str) -> dict:
        """Get Transaction Receipt
        
        --- Definitions ---
        {"name": "transaction_hash", "prompt": "transaction_hash", "default": "9483821e7e9d214a1ad218889d0dc3308a0f7f4b2fe4dc1129b2e77fe32e6e12"}
        """

        data = {
            "transaction_hash": hashb64(transaction_hash),
        }
        data = json.dumps(data)

        import time
        # Retry several times, waiting 1 second between retries
        num_retries = 30
        for i in range(num_retries):
            p = self._run_cmd([grcmd, "-d", data, "-plaintext", self.server, self.services["GetTransactionReceipt"]])
            if p.returncode == 0:
                break
            time.sleep(1)

        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")
            return

        tx_receipt = json.loads(p.stdout)

        # Build a pythonic transaction receipt
        tx_receipt["blockHash"] = hash(tx_receipt['blockHash'])
        tx_receipt['transactionHash'] = hash(tx_receipt['transactionHash'])
        tx_receipt['senderAddress'] = address(tx_receipt['senderAddress'])
        tx_receipt['receiverAddress'] = address(tx_receipt['receiverAddress'])
        tx_receipt['newAddress'] = address(tx_receipt['newAddress'])
        tx_receipt['gasUsed'] = b64str_to_int(tx_receipt['gasUsed'])

        if "logs" in tx_receipt:
            for log in tx_receipt["logs"]:
                log['address'] = address(log['address'])
                topics = log['topics']
                for j in range(len(topics)):
                    topics[j] = hash(topics[j])

        print(json.dumps(tx_receipt, ensure_ascii=False, indent=3))

        return tx_receipt



    def get_nonce(self, address: str) -> int:
        """Get Nonce
        
        --- Definitions ---
        {"name": "address", "prompt": "Address", "default": "54d0b0bc6cbbd54d0ec605cbf87819763445e70ef24fc85c20"}
        """

        a = string_to_b64str(address)
        data = {
            "address": a
        }
        data = json.dumps(data)

        p = self._run_cmd([grcmd, "-d", data, "-plaintext", self.server, self.services["GetNonce"]])
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")
            return 0
        out = json.loads(p.stdout)
        nonce_encoded = out["nonce"]

        nonce = b64str_to_int(nonce_encoded)
        print(f"Nonce: {nonce}")
        return nonce

    def get_latest_block(self):
        """Get Latest Block
        """
        p = self._run_cmd([grcmd, "-plaintext", self.server, self.services["GetLatestBlock"]])
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")
            return
        out = json.loads(p.stdout)
        print(f"{out}")

    def get_block_by_index(self, index: int):
        """Get Nonce
        
        --- Definitions ---
        {"name": "index", "type": "int", "prompt": "Block index", "default": 2000000}
        """

        data = {
            "block_index": index
        }
        data = json.dumps(data)

        p = self._run_cmd([grcmd, "-d", data, "-plaintext", self.server, self.services["GetBlockByIndex"]])
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")
            return
        out = json.loads(p.stdout)
        print(f"{out}")

    def list_balance_per_address(self):
        """List Balance Per Address
        """
        p = self._run_cmd([grcmd, "-plaintext", self.server, self.services["ListBalancePerAddress"]])
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")
            return
        out = json.loads(p.stdout)
        addresses = out["addresses"]
        for item in addresses:
            address = item["address"]
            address = base64.b64decode(address)
            balance = item["balance"]
            balance = b64str_to_int(balance)
            print(f"Address: {address}, balance: {balance}")


    def get_latest_balance(self, address: str):
        """Get Latest Balance
        
        --- Definitions ---
        {"name": "address", "prompt": "Address", "default": "54d0b0bc6cbbd54d0ec605cbf87819763445e70ef24fc85c20"}
        """

        a = string_to_b64str(address)
        data = {
            "address": a
        }
        data = json.dumps(data)

        p = self._run_cmd([grcmd, "-d", data, "-plaintext", self.server, self.services["GetLatestBalance"]])
        if p.returncode != 0:
            print(f"There was an error: {p.stderr}")
            return
        out = json.loads(p.stdout)
        balance = out["balance"]

        balance = b64str_to_int(balance)
        print(f"Balance: {balance}")

acc = Tolar(gserver)

