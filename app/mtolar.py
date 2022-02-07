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

from blockchain import trustframework as tf
from blockchain import wallet, certificates, safeisland, eutl, pubcred
from blockchain import christmas, compile, canismajor
from blockchain import tolar_hashnet

from utils.menu import Menu, invoke

acc = tolar_hashnet.acc

##########################################################################
##########################################################################
# The Main Interactive Menu
##########################################################################
##########################################################################

def main_menu():

    warning_message = ""
    try:
        tf.connect_blockchain(settings.BLOCKCHAIN_NODE_IP)
    except FileNotFoundError as e:
        print(e)
        warning_message = "[ATTENTION: no deployment artifacts found. Deploy Smart Contracts first]"
        wm = typer.style(warning_message, fg=typer.colors.BRIGHT_RED, bold=True)

    if settings.PRODUCTION:
        environ = "PROD"
    else:
        environ = "DEV"
    message = f"SmartContracts: {environ}, Blockchain Node: {settings.BLOCKCHAIN_NODE_IP} {warning_message}"
    main = Menu(title = "RedT Blockchain App Maintenance", message=message)

    tolarm = Menu(title = "Tolar Contracts Management")
    tolarm.set_options([
        ("Deploy Smart Contract", invoke, {"operation":acc.SendDeployContractTransaction}),
        ("SendExecuteFunctionTransaction", invoke, {"operation":acc.SendExecuteFunctionTransaction}),
        ("Try Call Transaction", invoke, {"operation":acc.TryCallTransaction}),
        ("Get Transaction Receipt", invoke, {"operation":acc.GetTransactionReceipt}),

        ("List all operations", invoke, {"operation":acc.list}),
        ("Create Keystore", invoke, {"operation":acc.create}),
        ("Open Keystore", invoke, {"operation":acc.open}),
        ("List Addresses", invoke, {"operation":acc.list_adddresses}),
        ("List Balance Per Address", invoke, {"operation":acc.list_balance_per_address}),
        ("Create New Address", invoke, {"operation":acc.create_new_address}),
        ("Import Raw Private Key", invoke, {"operation":acc.import_raw_private_key}),

        ("Get Nonce", invoke, {"operation":acc.get_nonce}),
        ("Get Latest Block", invoke, {"operation":acc.get_latest_block}),
        ("Get Latest Balance", invoke, {"operation":acc.get_latest_balance}),
        ("Get Block By Index", invoke, {"operation":acc.get_block_by_index}),

    ])


    fiware = Menu(title = "FIWARE Canis Major")
    fiware.set_options([
        ("Timestamp", invoke, {"operation":canismajor.m_timestamp}),
        ("Check access to timestamp", invoke, {"operation":canismajor.checktimestamp}),
        ("List all items", invoke, {"operation":canismajor.list_all}),
        ("List one item", invoke, {"operation":canismajor.list_one_item}),
    ])

    smartcontracts = Menu(title = "Smart Contracts Management")
    smartcontracts.set_options([
        ("Compile FIWARE Canis Major Smart Contracts", invoke, {"operation":compile.m_compile_canis_major}),
        ("Deploy the FIWARE Canis Major Smart Contracts", invoke, {"operation":compile.m_deploy_canis_major}),
        ("Compile the Standard Smart Contracts", invoke, {"operation":compile.m_compile}),
        ("Deploy the Standard Smart Contracts", invoke, {"operation":compile.m_deploy}),
    ])

    

    identities = Menu(title = "Identities")
    identities.set_options([
        ("Create/Update an Identity", invoke, {"operation":tf.m_create_identity}),
        ("Resolve a DID", invoke, {"operation":tf.m_get_DIDDocument}),
        ("Dump all identities", invoke, {"operation":tf.m_dump_all_identities}),
        ("Dump all identities starting at a node", invoke, {"operation":tf.m_dump_identities}),
    ])

    wallet_menu = Menu(title = "Wallet")
    wallet_menu.set_options([
        ("Create/Update an account", invoke, {"operation":wallet.m_create_account}),
        ("Query an account", invoke, {"operation":wallet.m_get_address}),
        ("Get Private Key (JWK format)", invoke, {"operation":wallet.m_key_JWK}),
        ("List all accounts", invoke, {"operation":tf.m_dump_all_identities}),
        ("WARNING!!! Erase ALL wallet accounts", invoke, {"operation":wallet.erase_wallet_db}),
    ])

    node_management = Menu(title = "Listings of the Trust system")
    node_management.set_options([
        ("Gets the owner of a given node in Alastria ENS", invoke, {"operation":tf.m_get_owner}),
        ("Get a subnode of a given node", invoke, {"operation":tf.m_get_subnode}),
        ("Set the name of a node for reverse resolution", invoke, {"operation":tf.m_setName}),
        ("Get the name assigned to a node", invoke, {"operation":tf.m_getName}),
    ])

    trusted_lists = Menu(title = "Trusted Lists")
    trusted_lists.set_options([
        ("Import into table the EU LOTL info", invoke, {"operation":eutl.m_import_eulotl_db}),
        ("Import into table the Spanish Trusted List", invoke, {"operation":eutl.m_import_estl_db}),
        ("Create in blockchain the EU List of Trusted Lists", invoke, {"operation":eutl.m_lotl}),
        ("Display from blockchain the Spanish Trusted List", invoke, {"operation":eutl.m_lotl_dump}),
    ])


    credentials = Menu(title = "COVID19 Credentials")
    credentials.set_options([
        ("Erase Covid19 database", invoke, {"operation":safeisland.erase_db}),
        ("Create a Covid19 certificate", invoke, {"operation":safeisland.m_new_certificate}),
        ("Create a Vaccination certificate", invoke, {"operation":safeisland.m_new_vaccination_certificate}),
        ("Display a Covid19 certificate", invoke, {"operation":safeisland.m_certificate}),
        ("Verify a certificate debug", invoke, {"operation":safeisland.verify_cert_token_debug}),
        ("Bootstrap Test credentials", invoke, {"operation":safeisland.create_test_credentials}),
        ("List all certificates", invoke, {"operation":safeisland.m_list_certificates}),
    ])

    pubcreds = Menu(title = "Public Credentials")
    pubcreds.set_options([
        ("Erase PubCred database", invoke, {"operation":pubcred.erase_db}),
        ("Create a Public Certificate", invoke, {"operation":pubcred.m_new_public_certificate}),
        ("Display a PubCred certificate", invoke, {"operation":pubcred.m_certificate}),
        ("Verify a certificate debug", invoke, {"operation":pubcred.verify_cert_token_debug}),
        ("Bootstrap Test credentials", invoke, {"operation":pubcred.create_test_credentials}),
        ("List all certificates", invoke, {"operation":pubcred.m_list_certificates}),
    ])

    christmas_menu = Menu(title = "Christmas")
    christmas_menu.set_options([
        ("Erase Christmas table", invoke, {"operation":christmas.erase_db}),
        ("Create identities of companies", invoke, {"operation":christmas.m_create_identities}),
        ("Create Christmas credentials", invoke, {"operation":christmas.m_create_credentials}),
        ("Create a Christmas certificate", invoke, {"operation":christmas.m_new_certificate}),
        ("Display a Christmas certificate", invoke, {"operation":christmas.m_certificate}),
        ("List all Christmas certificates", invoke, {"operation":christmas.m_list_certificates}),
    ])


    main.set_options([
        ("TOLAR management", tolarm.open),
        ("FIWARE Canis Major", fiware.open),
        ("Smart Contracts Management", smartcontracts.open),
        ("Bootstrap Identity Framework (Top Level Domain)", invoke, {"operation":tf.m_create_test_identities}),
        ("Identities", identities.open),
        ("COVID19 Credentials", credentials.open),
        ("PUBLIC Credentials", pubcreds.open),
        ("Trusted Lists", trusted_lists.open),
        ("Wallet (management of private keys)", wallet_menu.open),
        ("Node management", node_management.open),
        ("Dump Trust Framework", invoke, {"operation":tf.m_dump_tf}),        
    ])

    main.open()


if __name__ == '__main__':

    main_menu()
