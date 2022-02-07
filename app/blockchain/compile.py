# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------
# Compilation of Solidity Smart Contracts
# -------------------------------------------------------------------------

import os
import subprocess as sp
from hexbytes import HexBytes

from blockchain import trustframework as tf
from blockchain import wallet
from blockchain import redt

from settings import settings

def compile_solidity_file(filename):

    # Point to the full path of the file
    sourcefile_path = os.path.join(settings.CONTRACTS_DIR, filename)

    # Create the target directory if it does not exist
    os.makedirs(settings.CONTRACTS_OUTPUT_DIR, exist_ok=True)

    print(f"\n==> Generating ABI for {filename}")
    command_abi = f"./solc-static-linux {sourcefile_path} --evm-version byzantium --abi --overwrite -o {settings.CONTRACTS_OUTPUT_DIR}"
    sp.run(command_abi, shell=True, cwd=settings.SOLC_DIR, text=True, check=True)

    print(f"\n==> Generating BIN for {filename}")
    command_bin = f"./solc-static-linux {sourcefile_path} --evm-version byzantium --bin --overwrite -o {settings.CONTRACTS_OUTPUT_DIR}"
    sp.run(command_bin, shell=True, cwd=settings.SOLC_DIR, text=True, check=True)


def deploy_ENSRegistry(root_key: HexBytes):

    ENSRegistry_full_path = os.path.join(settings.CONTRACTS_OUTPUT_DIR, "ENSRegistry")
    print(f"Deploying {ENSRegistry_full_path}")
    success, tx_receipt, ens_address = redt.deploy_contract(
        ENSRegistry_full_path,
        private_key=root_key
    )
    if success == False:
        print("Error deploying the contract")
        print(tx_receipt)
        exit(1)

    return ens_address


def deploy_PublicResolver(ENS_address: str, deploy_key: HexBytes):

    PublicResolver_full_path = os.path.join(
        settings.CONTRACTS_OUTPUT_DIR, "PublicResolver")
    print(f"Deploying {PublicResolver_full_path}")
    success, tx_receipt, resolver_address = redt.deploy_public_resolver(
        PublicResolver_full_path,
        ens_address=ENS_address,
        private_key=deploy_key
    )
    if success == False:
        print("Error deploying the contract")
        exit(1)

    return resolver_address


def m_compile():
    """Compiles the Smart Contracts.
    Overwrites the currently compiled contracts

    --- Definitions ---
    """
    compile_solidity_file("PublicSelfDeclarations.sol")
    compile_solidity_file("ENSRegistry.sol")
    compile_solidity_file("PublicResolver.sol")

def m_compile_canis_major():
    """Compiles the Smart Contracts.
    Overwrites the currently compiled contracts

    --- Definitions ---
    """
    compile_solidity_file("Timestamper.sol")

def deploy_canis_major(root_key: HexBytes):

    Timestamper_full_path = os.path.join(settings.CONTRACTS_OUTPUT_DIR, "Timestamper")
    print(f"Deploying {Timestamper_full_path}")
    success, tx_receipt, ens_address = redt.deploy_contract(
        Timestamper_full_path,
        private_key=root_key
    )
    if success == False:
        print("Error deploying the contract")
        print(tx_receipt)
        exit(1)

    return ens_address


def m_deploy_canis_major():
    """WARNING: Deploys the Timestamper Smart Contract.
    This will forget the currently deployed contracts in the blockchain

    --- Definitions ---
    """
    # Create a new account
    print(f"\n==> Creating new account")
    new_account = wallet.new_account("Timestamper", "ThePassword")
    new_address = new_account.address
    new_key = new_account.key
    print(f"New account created and saved")

    # Deploy the Timestamper contract using this account
    print(f"\n==> Deploying Timestamper with account: {new_address}")
    Timestamper_address = deploy_canis_major(new_key)
    print(f"Timestamper contract deployed at address: {Timestamper_address}")


def m_deploy():
    """Deploys the Smart Contracts.
    This will forget the currently deployed contracts in the blockchain

    --- Definitions ---
    """
    # Create the ROOT account for deployment of the contracts
    print(f"\n==> Creating the root account")
    root_account = wallet.new_account("ROOT", "ThePassword")
    ROOT_address = root_account.address
    ROOT_key = root_account.key
    print(f"Root account created and saved")

    # Deploy the ENS contract using this account
    print(f"\n==> Deploying ENS with root account: {ROOT_address}")
    ENS_address = deploy_ENSRegistry(ROOT_key)
    print(f"ENS deployed at address: {ENS_address}")

    # Deploy the PublicResolver contract, associated to the ENS and with the same root key
    print(f"\n==> Deploying Publicresolver")
    PublicResolver_address = deploy_PublicResolver(ENS_address, ROOT_key)
    print(f"Publicresolver deployed at address: {PublicResolver_address}")

    # Reconnect to the blockchain, this time binding the contracts just deployed
    tf.connect_blockchain(settings.BLOCKCHAIN_NODE_IP)

    # Set the PublicResolver as the resolver of the ROOT node, so it can access all other nodes
    print(f"\n==> Set the PublicResolver as the resolver of the ROOT node")
    tf.ens.setResolver("root", PublicResolver_address, ROOT_key)
    print(f"Done")

    # And assign approval to the PublicResolver contract so it can call ENS methods
    tf.ens.setApprovalForAll(PublicResolver_address, True, ROOT_key)

    # And assign the name "root" to that special root node, to reverse-resolve its name_hash
    print(f"\n==> Assign the name root to the root node, for reverse resolution")
    success, tx_receipt, tx_hash = tf.resolver.setName(
        "root", "root", ROOT_key)
    print(f"Done")

