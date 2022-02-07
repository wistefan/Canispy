#!/usr/bin/python3

#################################################################################
#################################################################################
# TRUSTED LISTS MANAGEMENT
#################################################################################
#################################################################################

import xml.etree.ElementTree as ET
import urllib
import os
import logging
import sqlite3
from pprint import pprint
import xml.etree.ElementTree as ET

from blockchain import trustframework as tf
from blockchain import wallet

try:
    from devtools import debug
except ImportError:
    def debug(*arg):
        pass

# The settings for the system
from settings import settings

# Initialize logging
log = logging.getLogger(__name__)


def m_lotl():
    """Re-creates the blockchain ENS nodes with the EU List Of Trusted Lists."""

    # Get the ROOT account. We need its private key.
    ROOT_address, ROOT_key = wallet.account_from_name("ROOT", "ThePassword")

    # The ROOT account will initially own the whole hierarchy

    # Set the subnode "trust"
    print(f"\n==> Creating the 'trust' subnode")
    success, _, _ = tf.ens.setSubnodeOwner(
        node_name="root",
        label="trust",
        new_owner_address=ROOT_address,
        current_owner_key=ROOT_key
    )
    print(f"'trust' subnode created")

    # Assign the name for reverse resolution of its name_hash
    tf.resolver.setName("trust", "trust", ROOT_key)

    # Set the node "es.trust", representing the Spanish Trusted List
    print(f"\n==> Creating the 'es' (Spanish) subnode")
    success, _, _ = tf.ens.setSubnodeOwner(
        node_name="trust",
        label="es",
        new_owner_address=ROOT_address,
        current_owner_key=ROOT_key
    )
    print(f"'es' subnode created")

    # Assign the name for reverse resolution
    tf.resolver.setName("es.trust", "es.trust", ROOT_key)

    # Now we will create a subnode for each TSP service in Spain
    # For the moment, the owner of those nodes will be the ROOT
    # In the future, ownership will be transferred to the corresponding entities

    # Get the list of TSP services from the DB
    TSPs = get_normalized_TSPs()

    for tsp in TSPs:
        URI = tsp
        URI_clean = URI
        URI_clean = URI_clean.replace("www.", "")
        URI_clean = URI_clean.replace(".com", "")
        URI_clean = URI_clean.replace(".es", "")
        URI_clean = URI_clean.replace(".", "-")

        # Set the sub node depending from node "es.trust"
        print(f"\n==> Creating the '{URI}' subnode of 'es'")
        success, _, _ = tf.ens.setSubnodeOwner(
            node_name="es.trust",
            label=URI_clean,
            new_owner_address=ROOT_address,
            current_owner_key=ROOT_key
        )
        print(f"{URI} subnode created with name: {URI_clean+'.es.trust'}")

        # Assign the name for reverse resolution
        tf.resolver.setName(URI_clean+".es.trust",
                         URI_clean+".es.trust", ROOT_key)

        org = TSPs[tsp][0]["org"]
        print(f"Org: {org}")

        # Set the TSP basic data
        tf.resolver.setAlaTSP(
            node_name="es.trust",
            label=URI_clean,
            URI=URI,
            org=org,
            active=True,
            current_owner_key=ROOT_key
        )

        active = tf.resolver.AlaTSP(node_name=URI_clean+".es.trust")
        print(f"URI: {URI}, Org: {org}, Active: {active}")

        # Now create the services for this TSP
        for service in TSPs[tsp]:

            # Set the service data
            tf.resolver.addAlaTSPService(
                node_name="es.trust",
                label=URI_clean,
                X509SKI=service["X509SKI"],
                serviceName=service["name"],
                X509Certificate=bytes(service["X509Certificate"], "utf-8"),
                active=True,
                current_owner_key=ROOT_key
            )
            print(f"Service: {service['name']}")


def m_lotl_dump():
    """Displays the current Spanish Trusted List from the blockchain."""

    numberSubnodes = tf.ens.numberSubnodes("es.trust")
    print(f"Number of subnodes: {numberSubnodes}")

    # Iterate for each TSP
    for i in range(tf.ens.numberSubnodes("es.trust")):

        # Get the subnode (in name_hash format)
        tsp_node_hash = tf.ens.subnode("es.trust", i)
        print(f"    Name: {tf.resolver.nameFromHash(tsp_node_hash)}")

        # Get the data for the TSP
        URI, org, active = tf.resolver.AlaTSP(node_hash=tsp_node_hash)
        print(f"    URI: {URI}, Org: {org}, Active: {active}")

        # Get the number of services
        numServices = tf.resolver.AlaTSPNumberServices(node_hash=tsp_node_hash)
        print(f"    Num Services: {numServices}")

        # Iterate all services
        for i in range(numServices):
            X509SKI, serviceName, X509Certificate, active = tf.resolver.AlaTSPService(
                node_hash=tsp_node_hash,
                index=i
            )
            print(f"        X509SKI: {X509SKI}, {serviceName}")


def get_normalized_TSPs():
    """ Get the list of TSPs from the database."""

    db = get_db()

    services = db.execute(
        'SELECT * FROM tl WHERE cc = "es"'
    )

    # The table is de-normalized, so there are several record for TSPs with more than one service
    # Create a normalized structure

    TSPs = {}
    for s in services:
        URI = s["URI"]
        if URI in TSPs:
            TSPs[URI].append(s)
        else:
            TSPs[URI] = [s]

    return TSPs


def m_import_eulotl_db():
    """Import the EU LOTL XML info into the table."""

    print(f"\n==> Erasing and creating the EU LOTL database table")
    reset_eutl_table()
    print(f"EU LOTL database table created")


def m_import_estl_db():
    """Import the Spanish Trusted List XML info into the table."""

    print(f"\n==> Erasing and creating the Spanish Trusted List database table")
    reset_estl_table()
    print(f"Spanish Trusted List database table created")





def get_db():
    db_name = os.path.join(settings.DATABASE_DIR, "pubcred_config.sqlite")
    db = sqlite3.connect(db_name, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db


# Reset the root EU Trusted List table
# Process the XMl file with the information for each country,
# and creates a record in the table with he Country Code and the URL where the list is located
def reset_eutl_table():

    # Parse the XML file in memory
    eu_lotl_path = os.path.join(settings.TRUSTED_LISTS_DIR, 'eu-lotl.xml')
    tree = ET.parse(eu_lotl_path)
    root = tree.getroot()

    # tl is the dictionary that will hold the trusted list pointer for all countries
    tl = {}
    for c1 in root.iter("{http://uri.etsi.org/02231/v2#}OtherTSLPointer"):
        is_xml = False
        url = None
        for c2 in c1.iter("{http://uri.etsi.org/02231/v2#}TSLLocation"):
            url = c2.text
            if url.endswith(".xml"):
                is_xml = True
        if is_xml:
            territory = None
            for c2 in c1.iter("{http://uri.etsi.org/02231/v2#}SchemeTerritory"):
                territory = c2.text

            if territory:
                # Create a dict entry with the country code and url
                tl[territory] = url

    # Print the results of parsing
    pprint(tl)
    print("\n")

    # This is the schema for the table
    lotl_schema = """
    DROP TABLE IF EXISTS lotl;

    CREATE TABLE lotl (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cc TEXT UNIQUE NOT NULL,
    TSLLocation TEXT UNIQUE NOT NULL
    );
    """

    # Connect to the database and drop (erase) the table
    db = get_db()
    db.executescript(lotl_schema)

    # Insert a record for each entry in the dict
    for cc in tl:
        db.execute(
            'INSERT INTO lotl (cc, TSLLocation) VALUES (?, ?)',
            (cc, tl[cc])
        )
        print(f"Country: {cc}, URL: {tl[cc]}")

    # Save (commit) the changes
    db.commit()
    db.close()


# Reset the Spanish Trusted List. The table will be erased.
# Process the XMl file with the information with the spanish TSPs,
# and create a record in the table
def reset_estl_table():

    # Parse the file with the Spanish Trusted List info
    es_tl_path = os.path.join(settings.TRUSTED_LISTS_DIR, 'es-tl.xml')
    tree = ET.parse(es_tl_path)
    root = tree.getroot()

    # Create a list of dicts, each one with the info for a Qualified Service
    # There may be more than one service entry for a single TSP entity
    # This is OK, as it is the way the Trusted Lists are built
    TSPs = getAllTSPs(root)

    # This is the schema for the table
    # The fields are the following:
    #   cc: Country Code
    #   X509SKI: the SubjectKeyIdentifier field in the X509 certificate identifying the Service/TSP
    #   URI: the URI of the TSP providing the service
    #   org: the organization name, as specified inside the SubjectName field of the certificate
    #   name: the service name
    #   X509SubjectName: the Subjectname field of the certificate
    #   X509Certificate: the full certificate
    tl_schema = """
    DROP TABLE IF EXISTS tl;

    CREATE TABLE tl (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    VATID TEXT NOT NULL,
    cc TEXT  NOT NULL,
    X509SKI TEXT UNIQUE NOT NULL,
    URI TEXT NOT NULL,
    org TEXT NOT NULL,
    name TEXT NOT NULL,
    X509SubjectName TEXT NOT NULL,
    X509Certificate TEXT NOT NULL
    );
    """

    # Connect to the database and erase the table
    db = get_db()
    db.executescript(tl_schema)

    # Create a record for each service, even if a TSP provides more than one service.
    # The Country Code is fixed to 'es' (Spain)
    for tsp in TSPs:
        URI = tsp["URI"]
        VATID = tsp["VATID"]
        print(f"ID: {VATID} provides the services:")
        for service in tsp["services"]:
            cc = "es"
            ids = service["ids"]
            X509SKI = ids["X509SKI"]
            org = getOrganizationField(ids["X509SubjectName"])
            name = service["name"]
            X509SubjectName = ids["X509SubjectName"]
            X509Certificate = ids["X509Certificate"]

            print(f"    {URI}: {name}")
            db.execute(
                'INSERT INTO tl (VATID, cc, X509SKI, URI, org, name, X509SubjectName, X509Certificate) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (VATID, cc, X509SKI, URI, org, name,
                 X509SubjectName, X509Certificate)
            )

    # Save (commit) the changes
    db.commit()
    db.close()


ns_prefix = "{http://uri.etsi.org/02231/v2#}"


def ns(tag):
    return ns_prefix + tag


def isServiceTypeQC(srv):
    # The subtag ServiceTypeIdentifier should be http://uri.etsi.org/TrstSvc/Svctype/CA/QC
    srv_type_id = None
    for n in srv.iter(ns("ServiceTypeIdentifier")):
        srv_type_id = n.text
    if srv_type_id == "http://uri.etsi.org/TrstSvc/Svctype/CA/QC":
        return True
    else:
        return False


def isServiceGranted(srv):
    # The subtag ServiceStatus should be http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted
    srv_status = None
    for n in srv.iter(ns("ServiceStatus")):
        srv_status = n.text
    if srv_status == "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted":
        return True
    else:
        return False


def getServiceName(srv):
    srv_name = None
    for n in srv.iter(ns("ServiceName")):
        # Get the first child contents (supposedly the english one)
        srv_name = n[0].text
    return srv_name


def getServiceDigitalIds(srv):
    digitalIds = {}
    for n in srv.iter(ns("DigitalId")):
        id = n[0].tag.replace(ns_prefix, "")
        value = n[0].text

        if id in digitalIds:
            if digitalIds[id] == value:
                continue
            else:
                print(
                    "WARNING WARNING two digital ids with different values WARNING WARNING WARNING ")
                print(
                    "WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING ")

        digitalIds[id] = value

    return digitalIds


def getOrganizationField(sn):
    ss = sn.split(",")
    for d in ss:
        d = d.strip()
        if d.startswith("O="):
            result = d.replace("O=", "")
            return result


def getAllServices(element):

    # We will create a list of dictionaries, each with individual service data
    all_services = []

    # Search for all TSPService tags
    for srv in element.iter("{http://uri.etsi.org/02231/v2#}TSPService"):

        # We are interested only in Qualified Certificates for Signatures
        if not isServiceTypeQC(srv):
            # Get out from this iteration but continue with the loop
            continue

        # We are interested only in active ("granted") services
        if not isServiceGranted(srv):
            # Get out from this iteration but continue with the loop
            continue

        # Parse the XML and get the relevant data about the service
        name = getServiceName(srv)
        digitalIds = getServiceDigitalIds(srv)

        # Initialize the dictionary
        service = dict(
            name=name,
            ids=digitalIds
        )

        # Add the service to the list
        all_services.append(service)

    return all_services


def get_TSP_URI(srv):
    TSP_URI = None
    for n in srv.iter(ns("TSPInformationURI")):
        # Get the first child contents (supposedly the english one)
        TSP_raw_URI = n[0].text

        # Parse the URI
        parsed_url = urllib.parse.urlparse(TSP_raw_URI)

        # Get the host name (should be a domain name in this case)
        TSP_URI = parsed_url.hostname

        if TSP_URI is None:
            # The URL provided does not follow the syntax specifications in RFC 1808.
            # Just return it unchanged
            TSP_URI = TSP_raw_URI

    return TSP_URI


def get_VATID(srv):
    VATID = None
    for trade_name in srv.iter(ns("TSPTradeName")):
        for name in trade_name:
            if name.text.startswith("VATES-"):
                VATID = name.text
                break
    return VATID


def getAllTSPs(element):

    # We will create a list of dictionaries, each with individual service data
    all_TSPs = []

    # Search for all TrustServiceProvider tags
    for srv in element.iter("{http://uri.etsi.org/02231/v2#}TrustServiceProvider"):

        # For this TSP get its associated hostname address (in TSPInformationURI tag)
        URI = get_TSP_URI(srv)

        # Get the VATES information
        VATID = get_VATID(srv)

        # Get the list of services provided by the TSP
        # The same TSP may provide more than one service
        # Also, we are interested only in Qualified Certificates for Signature,
        # and of those, only in active state ("granted")
        # For this reason, the list may be empty and we skip that TSP
        services = getAllServices(srv)

        if len(services) == 0:
            continue

        # Initialize the dictionary
        TSP_list = dict(
            VATID=VATID,
            URI=URI,
            services=services
        )

        # Add the service to the list
        all_TSPs.append(TSP_list)

    return all_TSPs
