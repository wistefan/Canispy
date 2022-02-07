from typing import List

from merklelib import MerkleTree, beautify
import merklelib

# a sample hash function
# you can also omit it and the default hash function will be used

data: List[int] = []
for i in range(100):
    data.append(i)

# build a Merkle tree for that list
tree = MerkleTree(data)
print(tree)

leaf_to_verify = 54
proof = tree.get_proof(leaf_to_verify)

# now verify that A is in the tree
# you can also pass in the hash value of 'A'
# it will hash automatically if the user forgot to hash it
if tree.verify_leaf_inclusion(leaf_to_verify, proof):
    print(f'{leaf_to_verify} is in the tree')
else:
    print(f'{leaf_to_verify} is not in the tree')

tree.append(leaf_to_verify)

proof = tree.get_proof(leaf_to_verify)

# now verify that A is in the tree
# you can also pass in the hash value of 'A'
# it will hash automatically if the user forgot to hash it
if tree.verify_leaf_inclusion(leaf_to_verify, proof):
    print(f'{leaf_to_verify} is in the tree')
else:
    print(f'{leaf_to_verify} is not in the tree')

beautify(tree)

# jj = merklelib.jsonify(tree)
# print(jj)

print(len(tree.hexleaves))