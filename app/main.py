# Standard python library
import logging

# The Fastapi web server
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import uvicorn for debugging
import uvicorn

# The settings for the system
from settings import settings

# Acces to the bockchain
from blockchain import trustframework as tf

# Create logger
logging.basicConfig(
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

# Create the FastAPi server
app = FastAPI(
    title="FIWARE Canis Major with EBSI/Alastria APIs",
    description="FIWARE blockchain integration with SSI and Verifiable Credentials with interoperability EBSI-Alastria Red T",
    version="0.2.0",
    openapi_url="/api/v1/openapi.json",
)

# The routes for the Canis Major NGSI API functionality
from routers import ngsi_api
app.include_router(ngsi_api.router)

# The routes for Resolver APIs
from routers import resolver_api
app.include_router(resolver_api.router, include_in_schema=True)

# The routes for Issuer APIs
from routers import issuer_api
app.include_router(issuer_api.router, include_in_schema=False)

# The route for Verifying a credential
from routers import verify_credential_api
app.include_router(verify_credential_api.router, include_in_schema=False)

# Support for API keys to secure invocations of APIs
from fastapi_simple_security import api_key_router
app.include_router(api_key_router, prefix="/auth", tags=["API-key Authorization"])

# APIs to check for server health
from routers import server_health
app.include_router(server_health.router, include_in_schema=True)

# APIS to implement a simple, fast a secure messaging server
from routers import secure_messaging_router
app.include_router(secure_messaging_router.router, include_in_schema=False)

# For serving static assets.
# Should be the last route added because it is serving the root ("/")
#app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Template directory for dynamic HTML pages
templates = Jinja2Templates(directory="templates")

# Perform startup processing
@app.on_event("startup")
async def startup_event():
    """Connect to blockchain when starting the server"""

    log.info("######### Configuration values #########")
    if settings.PRODUCTION:
        log.info(f"Running in PRODUCTION")
    else:
        log.info(f"Running in DEVELOPMENT")
    log.info(f"Current directory: {settings.INITIAL_DIR}")
    log.info(f"SmartContract source dir: {settings.CONTRACTS_DIR}")
    log.info(f"SmartContract binary dir: {settings.CONTRACTS_OUTPUT_DIR}")
    log.info(f"Blockchain IP: {settings.BLOCKCHAIN_NODE_IP}")
    log.info(f"Database Dir: {settings.DATABASE_DIR}")
    
    tf.connect_blockchain(settings.BLOCKCHAIN_NODE_IP)
    log.info(f"Connected to the blockchain provider")

    log.info("########################################")


# This is for running the server in test mode
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
