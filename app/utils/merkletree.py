# My Merkle Hash Tree (MHT)

from typing import List, Tuple, Union

import hashlib
from hashlib import sha256
from math import log2
import json
from pprint import pprint

debug_enabled = False
def print_debug(text: str):
    if debug_enabled:
        print(text)

# This is the hash function to use. Update this variable to use another
hash_function = sha256

class MerkleError(Exception):
    pass

ROOT_NODE = "ROOT"
LEAF_NODE = "LEAF"
INTERIOR_NODE = "INTERIOR"
AUX_NODE = "AUXILIAR"

class Node(object):
    """Each node has, as attributes, references to left and right child nodes, parent,
    and sibling node. It can also be aware of whether it is on the left or right hand side (side).
    data is hashed automatically by default, but does not have to be, if prehashed param is set to True.
    """

    # Use __slots__ as a performance and space-saver technique
    # See https://docs.python.org/3.8/reference/datamodel.html?highlight=__slots__#object.__slots__
    #__slots__ = ['t', 'l', 'r', 'p', 'sib', 'side', 'val']

    def __init__(self,
        data,
        prehashed: bool = False,
        node_type=LEAF_NODE,
        level = 0,
        index = 0):

        if prehashed:
            self.value = data
        else:
            self.value = self._hash(data)

        self.node_type = node_type
        self.left_child = None
        self.right_child = None
        self.parent = None
        self.sibling = None
        self.side = None
        self.level = level
        self.index = index

    def _hash(self, text: Union[str, bytes]) -> bytes:
        if isinstance(text, str):
            text = bytes(text, "utf-8")
        h = hashlib.sha256()
        h.update(text)
        d = h.digest()
        return d

    def export(self):
        r = {
            'type': self.node_type,
            'level': self.level,
            'index': self.index,
            'value': self.value.hex(),
            'sibling': 0 if not self.sibling else self.sibling.value.hex(),
            'left_child': self.left_child,
            'right_child': self.right_child,
        }
        return r

    def __repr__(self):
        return json.dumps(self.export())

    def __str__(self):
        return self.export()
        

from json import JSONEncoder

class MHT_JSON_Encoder(JSONEncoder):
    def default(self, o):
        if type(o) == Node:
            return o.export()

        # If we do not recognize the type, let the base class raise the error
        return json.JSONEncoder.default(self, o)


class MerkleTree(object):
    """A Merkle tree implementation.  Added values are stored in a list until the tree is built.
    A list of data elements for Node values can be optionally supplied to the constructor.
    Data supplied to the constructor is hashed by default, but this can be overridden by
    providing prehashed=True in which case, node values should be hex encoded.
    """
    def __init__(self, leaves=[], prehashed: bool=False):
        self.root: Node = None
        self.leaves: List[Node] = []
        for i in range(len(leaves)):
            self.leaves.append(Node(leaves[i], prehashed=prehashed, level=0, index=i))

    def __str__(self):
        return json.dumps(self.export(), indent=3, cls=MHT_JSON_Encoder)

    def export(self):
        """Export the tree as a serializable Python object"""
        return self.root

    def __eq__(self, obj):
        return (self.root.value == obj.root.value) and (self.__class__ == obj.__class__)

    def add(self, data, prehashed=False):
        """Add a Node to the tree, providing data, which is hashed automatically.
        """
        # Create a new leaf node
        new_node = Node(data, prehashed=prehashed, node_type=LEAF_NODE, level=0)

        # Replace the last leaf node if it is an auxiliar node
        if len(self.leaves) > 0 and self.leaves[-1].node_type == AUX_NODE:
            self.leaves[-1] = new_node
        else:
            self.leaves.append(new_node)

    def add_node(self, data, prehashed=False):
        """Add new node recalculating appropriate hashes"""

        # Add a node to the leaves
        self.add(data, prehashed=prehashed)

        # Recalculate the tree hashes
        # TODO: optimize adding a new node recalculating only whay is needed
        # For the moment, rebuild the whole tree
        self.build()

    def build_MHT(self) -> Node:
        """Calculate the merkle root and make references between nodes in the tree.
        """
        self.root = self.MHT(self.leaves)
        return self.root

    def largest_power_of_two_smaller_than(self, n):
        p = int(log2(n))
        t = 2**p
        if t == n:
            return 2**(p - 1)
        return t

    def MHT(self, layer: List[Node], level = 0) -> Node:
        """Calculate the merkle root and make references between nodes in the tree.
        As per IETF-RFC6962:
        The hash of an empty list is the hash of an empty string:
            MTH({}) = SHA-256().

        The hash of a list with one entry (also known as a leaf hash) is:
            MTH({d(0)}) = SHA-256(0x00 || d(0)).

        For n > 1, let k be the largest power of two smaller than n (i.e.,
        k < n <= 2k).  The Merkle Tree Hash of an n-element list D[n] is then
        defined recursively as

            MTH(D[n]) = SHA-256(0x01 || MTH(D[0:k]) || MTH(D[k:n])),

        where || is concatenation and D[k1:k2] denotes the list {d(k1),
        d(k1+1),..., d(k2-1)} of length (k2 - k1).  (Note that the hash
        calculations for leaves and nodes differ.  This domain separation is
        required to give second preimage resistance.)
        """

        # Special case of empty list
        if len(layer) == 0:
            # MTH({}) = SHA-256()
            print_debug("EMPTY LIST")
            return Node(b'')

        # Special case of a single node in the layer, which should be a LEAF
        if len(layer) == 1:
            # MTH({d(0)}) = SHA-256(0x00 || d(0))
            print_debug(f"My Level-Index: {layer[0].level}, {layer[0].index}: {layer[0].value.hex()}")

            # If node is LEAF then it is already hashed, just return the node
            if layer[0].level == 0:
                return layer[0]

            # Otherwise, return the hash 
            print_debug(f"WARNING WARNING: Len 1, Level>0")
            return hash_function(layer[0].value).digest()
            #return hash_function(b'0' + layer[0].value)

        # MTH(D[n]) = SHA-256(0x01 || MTH(D[0:k]) || MTH(D[k:n]))
        # Layer with 2 or more nodes

        # Divide the list in two parts
        k = self.largest_power_of_two_smaller_than(len(layer))
        print_debug(f"Total {len(layer)}, selecting {len(layer[0:k])} and {len(layer[k:])}")

        # Recursively calculate each part of the list
        left_child = self.MHT(layer[0:k])
        print_debug(f"Left: {left_child.level}, {left_child.index}, {left_child.value.hex()}")
        right_child = self.MHT(layer[k:])
        print_debug(f"Right: {right_child.level}, {right_child.index}, {right_child.value.hex()}")

        # Create parent node of left and right
        my_level = left_child.level + 1
        my_index = left_child.index
        print_debug(f"My Level-Index: {my_level}, {my_index}")

        newnode = Node(left_child.value + right_child.value, node_type=INTERIOR_NODE, level=my_level, index=my_index)
        newnode.left_child, newnode.right_child = left_child, right_child
        left_child.side, right_child.side, left_child.parent, right_child.parent = 'L', 'R', newnode, newnode
        left_child.sibling, right_child.sibling = right_child, left_child

        return newnode
        #return hash_function(b'1' + left + right).digest()


    def build(self) -> bytes:
        """Calculate the merkle root and make references between nodes in the tree.
        """

        if not self.leaves:
            # MTH({}) = SHA-256()
            return hash_function(b'').digest()

        layer: List[Node] = self.leaves[::]
        level = 1
        while len(layer) != 1:
            layer = self._build_next_layer(layer, level)
            level = level + 1
        self.root = layer[0]
        self.root.node_type = ROOT_NODE
        return self.root.value

    def _build_next_layer(self, leaves: List[Node], level: int) -> List[Node]:
        """Private helper function to create the next aggregation level and put all references in place.
        """
        new: List[Node] = []
        # check if even number of leaves, add empty node at the end if not
        if len(leaves) % 2 == 1:
            leaves.append(Node(b'', node_type=AUX_NODE, level=level-1))
        for i in range(0, len(leaves), 2):
            left_child, right_child = leaves[i], leaves[i + 1]
            newnode = Node(left_child.value + right_child.value, node_type=INTERIOR_NODE, level=level)
            newnode.left_child, newnode.right_child = left_child, right_child
            left_child.side, right_child.side, left_child.parent, right_child.parent = 'L', 'R', newnode, newnode
            left_child.sibling, right_child.sibling = right_child, left_child
            new.append(newnode)
        return new

    def num_leaves(self):
        """Return the number of leaves, not including a possible AUX node at the end"""
        # Replace the last leave node if it an auxiliar node
        if len(self.leaves) > 0 and self.leaves[-1].node_type == AUX_NODE:
            return len(self.leaves) - 1
        else:
            return len(self.leaves)

    def inclusion_proof_by_index(self, index: int) -> List[Tuple]:
        """Assemble and return the chain leading from a given node to the merkle root of this tree.
        """

        # Check if index is within bounds
        if index < 0 or index >= self.num_leaves():
            raise MerkleError(f"Index {index} out of bounds")

        chain: List[Tuple] = []

        # Get the node for the index
        the_node = self.leaves[index]

        # Sanity check
        if the_node.level != 0 or the_node.index != index:
            raise MerkleError(f"Corrupted node data at index {index}")

        # Walk the tree up until a node has no parent, which is the ROOT node
        while the_node.parent:
            sibling = the_node.sibling
            print_debug(f"The node: {the_node.level}, {the_node.index}, {the_node.side}")
            print_debug(f"Sibling node: {sibling.level}, {sibling.index}, {sibling.side}")
            chain.append((sibling.level, sibling.index, sibling.side, sibling.value))
            the_node = the_node.parent
        return chain

    def get_all_chains(self) -> List[List[Tuple]]:
        """Assemble and return a list of all chains for all leaf nodes to the merkle root.
        """
        return [self.get_chain(i) for i in range(self.num_leaves())]

    def verify_inclusion_proof(self, index: int, hash: bytes, proof: List[Tuple]) -> bool:

        # Check if index is within bounds
        if index < 0 or index >= self.num_leaves():
            raise MerkleError(f"Index {index} out of bounds")

        leaf_node = self.leaves[index]

        h = leaf_node.value
        print_debug(h.hex())
        for item in proof:
            if item[2] == 'R':
                print_debug(f"{h.hex()} + {item[3].hex()}")
                h = hash_function(h + item[3]).digest()
            else:
                print_debug(f"{item[3].hex() + {h.hex()}}")
                h = hash_function(item[3] + h).digest()
            print_debug(h.hex())

        print_debug(f"Target hash: {h.hex()}")
        
        if h == self.root.value:
            return True
        else:
            return False

    def dump_tree(self, node: Node = None, indent: str =""):
        if node == None:
            node = self.root

        print_debug(f"{indent}Node: {node.level}, {node.index}, {node.side}: {node.value.hex()}")
        
        left_child = node.left_child
        right_child = node.right_child

        # if left_child:
        #     print_debug(f"   Left: {left_child.level}, {left_child.index}, {left_child.side}")
        # if right_child:
        #     print_debug(f"   Right: {right_child.level}, {right_child.index}, {right_child.side}")

        if left_child:
            self.dump_tree(left_child, indent=indent + "   ")
        if right_child:
            self.dump_tree(right_child, indent=indent + "   ")




# data = [b"hola", b"que", b"tal", b"estas", b"hoy"]

# for i in range(10):
#     data = [b"hola" for j in range(i)]
#     print(data)
#     m0 = MerkleTree(data)
#     mm = m0.build_MHT()
#     print(f"MHT Level: {mm.level} {mm.value.hex()}")
#     print("Chains")
#     pprint(m0.get_all_chains())
#     print()


# async def main():
#     outer_loop = 11
#     inner_loop = 100000
#     operations = outer_loop * inner_loop

#     f = myM(mkItems=1000)
#     f.reset_counter()

#     start_time = time.monotonic()
    

#     ops = 0
#     for i in range(outer_loop):
#         st2 = time.monotonic()
#         for j in range(inner_loop):
#             await f.put('Identifier', 'This is the value')
#             ops += 1

#     files_processed = f.get_counter()
#     f.close()

#     now = time.monotonic()
#     e2 = now - st2

#     print(f'Innerloop: {inner_loop/e2}')

#     elapsed_time = now - start_time
#     operations_second = (operations) / elapsed_time

#     print(f"{operations} performed in {elapsed_time} seconds")
#     print(f"Iterations/second: {operations_second}")

#     print(f'Files processed: {files_processed}')

if __name__ == '__main__':
    asyncio.run(main())



# m = MerkleTree(data)
# r = m.build_MHT()

# print("\nDumping Tree")
# m.dump_tree()

# proof_index = 0
# print("\nInclusion proof")
# p = m.inclusion_proof_by_index(proof_index)
# print()

# for item in p:
#     print(f"{item[0]}, {item[1]}, {item[2]}, {item[3].hex()}")

# print(m.verify_inclusion_proof(proof_index, r.value, p))

