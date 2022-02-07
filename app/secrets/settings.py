# WARNING! WARNING! WARNING! 
# Make sure this file is not synced with Github

import os
from pathlib import Path

# For the data models
from typing import Any, Dict, Tuple, Optional, cast
from pydantic import BaseModel, BaseSettings


class SecretSettings(BaseModel):

    PRODUCTION: bool = True

    BLOCKCHAIN_NODE_IP: str = "HTTP://15.236.0.91:22000"

    # Directories with sources of the Smart Contracts and deployment artifacts
    CONTRACTS_SUBDIR = os.path.join("smartcontracts", "src")
    CONTRACTS_OUTPUT_SUBDIR = os.path.join("smartcontracts", "test_deploy")

    # Configuration of FastAPI API_KEY security system
    FASTAPI_SIMPLE_SECURITY_HIDE_DOCS = True
    FASTAPI_SIMPLE_SECURITY_DB_LOCATION = os.path.join("apikeys.sqlite")
    FAST_API_SIMPLE_SECURITY_AUTOMATIC_EXPIRATION = 15
    FASTAPI_SIMPLE_SECURITY_SECRET = "dd4342a2-7d48-4d00-a118-21e63ac3449e"


def override_settings(home_path: str, settings: dict) -> dict:
    secret_settings = SecretSettings(INITIAL_DIR = home_path)

    ss = secret_settings.dict()
    for key in ss:
#        print(f"Set {key}, {ss[key]}")
        settings[key] = ss[key]

    return settings
