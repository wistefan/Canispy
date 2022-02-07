import time

# From this project packages
from blockchain import trustframework as tf
from blockchain import wallet, didutils, safeisland, pubcred, redt

from devtools import debug
from hexbytes import HexBytes

import rlp

w3 = redt.setup_provider("HTTP://15.236.0.91:22000")
print(f"Version: {w3.clientVersion}")
# print(f"Gas price: {w3.eth.gasPrice}")
# print(f"Peer count: {w3.net.peer_count}")
# print(f"Admin datadir: {w3.geth.admin.datadir()}")
#debug(w3.geth.admin.node_info())
#debug(w3.geth.personal.list_accounts())
#debug(w3.geth.txpool.inspect())

# Get the block header
block = w3.eth.get_block('latest')
debug(block)
# Get the block hash which was signed
block_hash = block["hash"]
print(f"Block: {block_hash.hex()}")

# Extradata includes signers
extradata = block["proofOfAuthorityData"]
vanity = extradata[:32]

# All the seals go here
seal_info = extradata[32:]
decoded = rlp.decode(seal_info)

# Extract validators
validators = decoded[0]
print(f"Validators ({len(validators)}) - {len(validators[0])}")
for val in validators:
    print(f"\t{val.hex()}")
print()

# Extract the seals
seal = decoded[1]
signer = w3.eth.account.recoverHash(block_hash, signature=seal)
print(f"Seal: {signer}")
print()

from eth_account import messages
from eth_utils.crypto import keccak

seals = decoded[2]
print(f"Commited Seals ({len(seals)} - {len(seals[0])})")
for s in seals:
    signer = w3.eth.account.recoverHash(block_hash, signature=s)
    print(f"\t{signer}")



exit()

def handle_event(event):
    print(type(event))

def log_loop(event_filter, poll_interval):
    while True:
        block = w3.eth.get_block('latest')
        extradata = block["proofOfAuthorityData"]
        print(type(extradata))
        decoded = rlp.decode(extradata)

        # for event in event_filter.get_new_entries():
        #     handle_event(event)
        time.sleep(poll_interval)

def main():
    block_filter = w3.eth.filter('latest')
    log_loop(block_filter, 4)

if __name__ == '__main__':
    main()