# For the data models
from typing import Dict, Optional, cast, Tuple
from pydantic import BaseModel, BaseSettings

# The reply messaje
class DID_components(BaseModel):
    method: str
    protocol: str
    instance: str
    address: str

class DIDParseError(Exception):
    pass

# Parse a DID into its components and check consistency
def parseDid(did: str) -> Tuple[str, DID_components]:
    """Parse a DID into its components and check consistency

    We support four DIDs: ebsi, elsi, ala, peer.
    Until EBSI is operational, we have made a basic implementation on Red T.

    The method for Legal Entities is did:elsi, where their DID is public and well-known.

    The name ELSI stands for (E)TSI (L)egal person (S)emantics (I)dentifier, and corresponds to the 
    information that should be included in the "organizationIdentifier" attribute as described in the
    European Norm ETSI EN 319 412-1, related to digital signatures, peer entity authentication, data
    authentication as well as data confidentiality.

    The structure of the DID (after the initial "did:elsi:" prefix) is:
       - 3 character legal person identity type reference;
       - 2 character ISO 3166 [2] country code;
       - hyphen-minus "-" (0x2D (ASCII), U+002D (UTF-8)); and
       - identifier (according to country and identity type reference).

    For the three initial characters ETSI EN 319 412-1 gives two options, but for the moment we
    only support the first one:
       - "VAT" for identification based on a national value added tax identification number.

    For example, the DID for Metrovacesa (metrovacesa.com) is "did:elsi:VATES-A87471264"
    """

    did_struct = {}

    # Split the DID using the separator ":"
    didc = did.split(":")

    # The first component should be "did"
    if didc[0] != "did" or len(didc) < 3:
        raise DIDParseError("Incorrect DID format")

    # The method is the second component (index starts at 0)
    method = didc[1]
    did_struct["method"] = method

    # Address is the last component (there may be more, depending on the method)
    did_struct["address"] = didc[-1]

    if method == "ala":
        # Process Alastria DIDs
        if len(didc) < 5:
            raise DIDParseError("Incorrect Alastria DID format")
        did_struct["protocol"] = didc[2]
        did_struct["instance"] = didc[3]

    elif method  == "elsi":
        # VAT DID method spec
        if len(didc) != 3:
            raise DIDParseError("Incorrect ELSI DID format")

    elif method  == "peer":
        # Peer DID method spec
        if len(didc) != 3:
            raise DIDParseError("Incorrect Peer DID format")

    elif method  == "ebsi":
        # EBSI DID method spec
        if len(didc) != 3:
            raise DIDParseError("Incorrect EBSI DID format")

    else:
        raise DIDParseError("DID method not recognized")
    
    return did_struct

