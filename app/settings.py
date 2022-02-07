# -*- coding: utf-8 -*-
# -----------------------
# FastAPI server settings
# -----------------------

import os
from pathlib import Path

# For the data models
from typing import Any, Dict, Tuple, Optional, cast
from pydantic import BaseModel, BaseSettings

from devtools import debug
from attributedict.collections import AttributeDict

# The directory where this file lives
INITIAL_DIR: str = os.path.dirname(os.path.abspath(__file__))

# Default settings
class Settings(BaseModel):

    # Address of the blockchain node to use
    BLOCKCHAIN_NODE_IP: str = "HTTP://127.0.0.1:7545"

    # Set this to True to use production resources
    PRODUCTION: bool = False
    BLOCKCHAIN_NETWORK = "REDT"

    # Directories with sources of the Smart Contracts and deployment artifacts
    CONTRACTS_SUBDIR = os.path.join("smartcontracts", "src")
    CONTRACTS_OUTPUT_SUBDIR = os.path.join("smartcontracts", "test_deploy")

    # Location of Solidity compiler
    SOLC_SUBDIR = os.path.join("solc")

    # Location of EUTL input files (XML format)
    TRUSTED_LISTS_SUBDIR = os.path.join("eutl")

    # Location and name of the SQLite database with local config data
    DATABASE_SUBDIR = os.path.join("db")

    # Location of the Tolar artifacts
    TOLAR_SUBDIR = os.path.join("tolar")

    # Protect the server against clients sending big requests
    MAX_CONTENT_LENGTH: int = 30000

    # Configuration for the cache of the Secure Messaging Server
    TTLCACHE_NUM_ELEMENTS: int = 10000
    TTLCACHE_EXPIRATION: int = 60

    # Configuration of FastAPI API_KEY security system
    # WARNING! The settings here are for testing purposes only
    # The production ones should be set in a settings file in the "secrets" directory
    FASTAPI_SIMPLE_SECURITY_HIDE_DOCS = True
    FASTAPI_SIMPLE_SECURITY_DB_NAME = os.path.join("apikeys.sqlite")
    FAST_API_SIMPLE_SECURITY_AUTOMATIC_EXPIRATION = 15
    FASTAPI_SIMPLE_SECURITY_SECRET = "dd4342a2-7d48-4d00-a118-21e63ac3449e"


settings = Settings().dict()

try:
    from secrets.settings import override_settings
    settings = override_settings(INITIAL_DIR, settings)
except Exception as e:
    print(e)

# Build the absolute paths from the relative ones
settings["INITIAL_DIR"] = INITIAL_DIR
settings["CONTRACTS_DIR"] = os.path.join(INITIAL_DIR, settings["CONTRACTS_SUBDIR"])
settings["CONTRACTS_OUTPUT_DIR"] = os.path.join(INITIAL_DIR, settings["CONTRACTS_OUTPUT_SUBDIR"])
settings["SOLC_DIR"] = os.path.join(INITIAL_DIR, settings["SOLC_SUBDIR"])
settings["TRUSTED_LISTS_DIR"] = os.path.join(INITIAL_DIR, settings["TRUSTED_LISTS_SUBDIR"])
settings["DATABASE_DIR"] = os.path.join(INITIAL_DIR, settings["DATABASE_SUBDIR"])
settings["DATABASE_NAME"] = os.path.join(settings["DATABASE_DIR"], "pubcred_config.sqlite")
settings["FASTAPI_SIMPLE_SECURITY_DB_LOCATION"] = os.path.join(settings["DATABASE_DIR"], "pubcred_config.sqlite")

settings["TOLAR_DIR"] = os.path.join(INITIAL_DIR, settings["TOLAR_SUBDIR"])

settings = AttributeDict(settings)

#debug(settings)